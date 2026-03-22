// SPDX-License-Identifier: Apache-2.0
/*
 * File        : spi_slave.v
 * Author      : Peter Szentkuti
 * Description : SPI slave for register read and write
 *
 * Reads CS_N, SCK and MOSI with clk_i and handles one command byte and one
 * data byte while CS_N stays low. For reads, the selected register byte is
 * sent on MISO during the second byte. After those two bytes, later SCK edges
 * do not start another transfer until CS_N goes high
 */

`default_nettype none
`timescale 1ns / 1ps

// SPI mode 0 slave that accepts one command byte and one data byte
// Keep SPI_SCK at clk_i / 8 or slower and keep CS_N high between frames
module spi_slave (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       spi_cs_ni,
  input  wire       spi_sck_i,
  input  wire       spi_mosi_i,
  input  wire [7:0] read_data_i,
  output wire [3:0] write_address_o,
  output wire [7:0] write_data_o,
  output wire       write_enable_o,
  output wire [3:0] read_address_o,
  output wire       read_active_o,
  output wire       access_pulse_o,
  output wire       miso_data_o,
  output wire       miso_output_enable_o
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
  reg [6:0] tx_shift_q;
  reg [6:0] tx_shift_d;

  // State for the current transfer
  reg [2:0] bit_count_q;
  reg [2:0] bit_count_d;
  reg       cmd_byte_q;
  reg       cmd_byte_d;
  reg       read_cmd_q;
  reg       read_cmd_d;
  reg       cmd_ok_q;
  reg       cmd_ok_d;
  reg       read_load_q;
  reg       read_load_d;
  reg       frame_done_q;
  reg       frame_done_d;

  // Stored register address and write byte
  reg [3:0] write_address_q;
  reg [3:0] write_address_d;
  reg [7:0] write_data_q;
  reg [7:0] write_data_d;

  // Read and write result for the current transfer
  reg       write_enable_q;
  reg       write_enable_d;
  reg [3:0] read_address_q;
  reg [3:0] read_address_d;
  reg       read_active_q;
  reg       read_active_d;
  reg       access_pulse_q;
  reg       access_pulse_d;
  reg       miso_data_q;
  reg       miso_data_d;
  reg       miso_output_enable_q;
  reg       miso_output_enable_d;

  // Read the SPI pins with clk_i before finding CS_N and SCK edges
  wire       cs_fall = (cs_sync_q[2:1] == 2'b10);
  wire       cs_rise = (cs_sync_q[2:1] == 2'b01);
  wire       cs_low = ~cs_sync_q[2];
  wire       sck_rise = (sck_sync_q[2:1] == 2'b01);
  wire       sck_fall = (sck_sync_q[2:1] == 2'b10);

  // Build the full received byte from the stored bits and the newest MOSI bit
  wire [7:0] rx_byte = {rx_shift_q, mosi_sync_q[1]};

  // Only command bits [6:4] = 000 are accepted
  wire       cmd_ok = (rx_byte[6:4] == 3'b000);

  // Drive the stored results out of the block
  assign write_address_o = write_address_q;
  assign write_data_o = write_data_q;
  assign write_enable_o = write_enable_q;
  assign read_address_o = read_address_q;
  assign read_active_o = read_active_q;
  assign access_pulse_o = access_pulse_q;
  assign miso_data_o = miso_data_q;
  assign miso_output_enable_o = miso_output_enable_q;

  // Store all state with clk_i
  always @(posedge clk_i or negedge rst_ni) begin : spi_state_ff
    if (!rst_ni) begin
      cs_sync_q <= 3'b111;
      sck_sync_q <= 3'b000;
      mosi_sync_q <= 2'b00;
      rx_shift_q <= 7'h00;
      tx_shift_q <= 7'h00;
      bit_count_q <= 3'd0;
      cmd_byte_q <= 1'b1;
      read_cmd_q <= 1'b0;
      cmd_ok_q <= 1'b0;
      read_load_q <= 1'b0;
      frame_done_q <= 1'b0;
      write_address_q <= 4'h0;
      write_data_q <= 8'h00;
      write_enable_q <= 1'b0;
      read_address_q <= 4'h0;
      read_active_q <= 1'b0;
      access_pulse_q <= 1'b0;
      miso_data_q <= 1'b0;
      miso_output_enable_q <= 1'b0;
    end else begin
      cs_sync_q <= cs_sync_d;
      sck_sync_q <= sck_sync_d;
      mosi_sync_q <= mosi_sync_d;
      rx_shift_q <= rx_shift_d;
      tx_shift_q <= tx_shift_d;
      bit_count_q <= bit_count_d;
      cmd_byte_q <= cmd_byte_d;
      read_cmd_q <= read_cmd_d;
      cmd_ok_q <= cmd_ok_d;
      read_load_q <= read_load_d;
      frame_done_q <= frame_done_d;
      write_address_q <= write_address_d;
      write_data_q <= write_data_d;
      write_enable_q <= write_enable_d;
      read_address_q <= read_address_d;
      read_active_q <= read_active_d;
      access_pulse_q <= access_pulse_d;
      miso_data_q <= miso_data_d;
      miso_output_enable_q <= miso_output_enable_d;
    end
  end

  always @* begin : spi_next_state_comb
    // Keep the current values unless the SPI transfer changes them
    cs_sync_d = {cs_sync_q[1:0], spi_cs_ni};
    sck_sync_d = {sck_sync_q[1:0], spi_sck_i};
    mosi_sync_d = {mosi_sync_q[0], spi_mosi_i};
    rx_shift_d = rx_shift_q;
    tx_shift_d = tx_shift_q;
    bit_count_d = bit_count_q;
    cmd_byte_d = cmd_byte_q;
    read_cmd_d = read_cmd_q;
    cmd_ok_d = cmd_ok_q;
    read_load_d = read_load_q;
    frame_done_d = frame_done_q;
    write_address_d = write_address_q;
    write_data_d = write_data_q;
    write_enable_d = 1'b0;
    read_address_d = read_address_q;
    read_active_d = read_active_q;
    access_pulse_d = 1'b0;
    miso_data_d = miso_data_q;
    miso_output_enable_d = miso_output_enable_q;

    // Any CS edge clears a partial transfer and returns to the command byte
    if (cs_rise || cs_fall) begin
      rx_shift_d = 7'h00;
      tx_shift_d = 7'h00;
      bit_count_d = 3'd0;
      cmd_byte_d = 1'b1;
      read_cmd_d = 1'b0;
      cmd_ok_d = 1'b0;
      read_load_d = 1'b0;
      frame_done_d = 1'b0;
      read_active_d = 1'b0;
      miso_data_d = 1'b0;
      miso_output_enable_d = 1'b0;
    end else begin
      // Sample MOSI on SCK rising edges
      if (cs_low && !frame_done_q && sck_rise) begin
        if (bit_count_q == 3'd7) begin
          bit_count_d = 3'd0;

          if (cmd_byte_q) begin
            // The first byte selects read or write and gives the register address
            // Bit 7 selects read when the command form is valid
            cmd_byte_d = 1'b0;
            cmd_ok_d = cmd_ok;
            read_cmd_d = cmd_ok && rx_byte[7];
            read_address_d = rx_byte[3:0];
            write_address_d = rx_byte[3:0];
            read_load_d = cmd_ok && rx_byte[7];
            read_active_d = 1'b0;
            miso_output_enable_d = 1'b0;
          end else begin
            // The second byte ends the transfer and may store one write byte
            frame_done_d = 1'b1;
            read_load_d = 1'b0;
            read_active_d = 1'b0;
            miso_output_enable_d = 1'b0;

            if (cmd_ok_q) begin
              access_pulse_d = 1'b1;

              if (!read_cmd_q) begin
                write_data_d = rx_byte;
                write_enable_d = 1'b1;
              end
            end
          end
        end else begin
          // Shift the partial byte until all eight bits have arrived
          rx_shift_d = {rx_shift_q[5:0], mosi_sync_q[1]};
          bit_count_d = bit_count_q + 3'd1;
        end
      end

      // During a read, the host still sends a second byte while the register
      // byte is sent on MISO
      // Shift read data out on SCK falling edges
      if (cs_low &&
          !frame_done_q &&
          !cmd_byte_q &&
          cmd_ok_q &&
          read_cmd_q &&
          sck_fall) begin
        if (read_load_q) begin
          // Load the read byte after the command byte is finished
          read_load_d = 1'b0;
          read_active_d = 1'b1;
          tx_shift_d = read_data_i[6:0];
          miso_data_d = read_data_i[7];
          miso_output_enable_d = 1'b1;
        end else if (read_active_q) begin
          // Shift one read bit each falling edge until the byte is done
          tx_shift_d = {tx_shift_q[5:0], 1'b0};
          miso_data_d = tx_shift_q[6];
        end
      end
    end
  end

endmodule // spi_slave

`default_nettype wire
