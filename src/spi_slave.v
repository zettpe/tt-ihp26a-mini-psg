// SPDX-License-Identifier: Apache-2.0
/*
 * File   : spi_slave.v
 * Author : Peter Szentkuti
 *
 * SPI slave
 *
 * Samples the Mode 0 SPI pins with clk_i and does not use spi_sck_i as an
 * internal clock. Accepts one write frame with one command byte followed
 * by one data byte, then pulses write_enable_o for one clk_i cycle when
 * the frame is accepted.
 *
 * Interface
 * - SPI Mode 0
 * - CS_N is active low
 * - Write only interface with no read data path
 *
 * Frame format
 * - One frame is one command byte followed by one data byte
 * - Command bits [7:4] must be 0000
 * - Command bits [3:0] select the write address
 * - The second byte is the write data
 * - Any CS_N edge aborts a partial frame
 * - Extra clocks after the data byte are ignored until CS_N returns high
 *
 * External timing requirements
 * - CS_N, SCK and MOSI are sampled with clk_i
 * - SPI_SCK must not exceed clk_i / 8
 * - Keep SCK low and high for at least 4 clk_i cycles each
 * - Present MOSI in Mode 0 form and keep it stable around each SCK rising edge
 * - Take CS_N low at least 4 clk_i cycles before the first SCK rising edge
 * - Keep CS_N low at least 4 clk_i cycles after the last SCK falling edge
 * - Keep CS_N high at least 4 clk_i cycles between frames
 */

`default_nettype none

module spi_slave (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       spi_cs_ni,
  input  wire       spi_sck_i,
  input  wire       spi_mosi_i,
  output wire [3:0] write_address_o,
  output wire [7:0] write_data_o,
  output wire       write_enable_o
);

  // Stored SPI pin values after the clk_i input stages
  reg [2:0] cs_sync_q;
  reg [2:0] cs_sync_d;
  reg [2:0] sck_sync_q;
  reg [2:0] sck_sync_d;
  reg [1:0] mosi_sync_q;
  reg [1:0] mosi_sync_d;

  // Shift storage for the current byte
  reg [6:0] rx_shift_q;
  reg [6:0] rx_shift_d;

  // State for the current transfer
  reg [2:0] bit_count_q;
  reg [2:0] bit_count_d;
  reg       cmd_byte_q;
  reg       cmd_byte_d;
  reg       cmd_ok_q;
  reg       cmd_ok_d;
  reg       frame_done_q;
  reg       frame_done_d;

  // Stored register address and write byte
  reg [3:0] write_address_q;
  reg [3:0] write_address_d;
  reg [7:0] write_data_q;
  reg [7:0] write_data_d;

  // Write result for the current transfer
  reg       write_enable_q;
  reg       write_enable_d;

  // Find CS_N and SCK edges after the clk_i input stages
  wire       cs_fall = (cs_sync_q[2:1] == 2'b10);
  wire       cs_rise = (cs_sync_q[2:1] == 2'b01);
  wire       cs_low = ~cs_sync_q[2];
  wire       sck_rise = (sck_sync_q[2:1] == 2'b01);

  // Build the full byte from the stored bits and the newest MOSI bit
  wire [7:0] rx_byte = {rx_shift_q, mosi_sync_q[1]};

  // Only write command bits [7:4] = 0000 are accepted
  wire       cmd_ok = (rx_byte[7:4] == 4'b0000);

  // Drive the last accepted write out of the block
  assign write_address_o = write_address_q;
  assign write_data_o = write_data_q;
  assign write_enable_o = write_enable_q;

  // Store all state with clk_i
  always @(posedge clk_i or negedge rst_ni) begin : spi_state_ff
    if (!rst_ni) begin
      cs_sync_q <= 3'b111;
      sck_sync_q <= 3'b000;
      mosi_sync_q <= 2'b00;
      rx_shift_q <= 7'h00;
      bit_count_q <= 3'd0;
      cmd_byte_q <= 1'b1;
      cmd_ok_q <= 1'b0;
      frame_done_q <= 1'b0;
      write_address_q <= 4'h0;
      write_data_q <= 8'h00;
      write_enable_q <= 1'b0;
    end else begin
      cs_sync_q <= cs_sync_d;
      sck_sync_q <= sck_sync_d;
      mosi_sync_q <= mosi_sync_d;
      rx_shift_q <= rx_shift_d;
      bit_count_q <= bit_count_d;
      cmd_byte_q <= cmd_byte_d;
      cmd_ok_q <= cmd_ok_d;
      frame_done_q <= frame_done_d;
      write_address_q <= write_address_d;
      write_data_q <= write_data_d;
      write_enable_q <= write_enable_d;
    end
  end

  always @* begin : spi_next_state_comb
    // Sample the SPI pins every clk_i cycle, hold the transfer state by
    // default and pulse write_enable_o only on a full write
    cs_sync_d = {cs_sync_q[1:0], spi_cs_ni};
    sck_sync_d = {sck_sync_q[1:0], spi_sck_i};
    mosi_sync_d = {mosi_sync_q[0], spi_mosi_i};
    rx_shift_d = rx_shift_q;
    bit_count_d = bit_count_q;
    cmd_byte_d = cmd_byte_q;
    cmd_ok_d = cmd_ok_q;
    frame_done_d = frame_done_q;
    write_address_d = write_address_q;
    write_data_d = write_data_q;
    write_enable_d = 1'b0;

    // Any CS edge clears a partial transfer and returns to the command byte
    if (cs_rise || cs_fall) begin
      rx_shift_d = 7'h00;
      bit_count_d = 3'd0;
      cmd_byte_d = 1'b1;
      cmd_ok_d = 1'b0;
      frame_done_d = 1'b0;
    end else begin
      // Sample MOSI on SCK rising edges
      if (cs_low && !frame_done_q && sck_rise) begin
        if (bit_count_q == 3'd7) begin
          bit_count_d = 3'd0;

          if (cmd_byte_q) begin
            // The first byte gives the register address
            cmd_byte_d = 1'b0;
            cmd_ok_d = cmd_ok;
            write_address_d = rx_byte[3:0];
          end else begin
            // The second byte ends the transfer and may store one write byte
            frame_done_d = 1'b1;

            if (cmd_ok_q) begin
              write_data_d = rx_byte;
              write_enable_d = 1'b1;
            end
          end
        end else begin
          // Shift the partial byte until all eight bits have arrived
          rx_shift_d = {rx_shift_q[5:0], mosi_sync_q[1]};
          bit_count_d = bit_count_q + 3'd1;
        end
      end
    end
  end

endmodule // spi_slave
