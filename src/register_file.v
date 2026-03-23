// SPDX-License-Identifier: Apache-2.0
/*
 * File        : register_file.v
 * Author      : Peter Szentkuti
 * Description : Register file with write masking
 *
 * Stores register values, keeps the write masks and
 * returns the selected byte for the given read address
 */

`default_nettype none
`timescale 1ns / 1ps

// Store register values
// Unmapped addresses return all 0s
module register_file (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       write_enable_i,
  input  wire [3:0] write_address_i,
  input  wire [7:0] write_data_i,
  input  wire [3:0] read_address_i,
  output reg  [7:0] read_data_o,
  output wire [7:0] control_value_o,
  output wire [7:0] note_a_value_o,
  output wire [7:0] channel_a_control_value_o,
  output wire [7:0] note_b_value_o,
  output wire [7:0] channel_b_control_value_o,
  output wire [7:0] volume_ab_value_o,
  output wire [7:0] noise_control_value_o,
  output wire [7:0] envelope_control_value_o,
  output wire [7:0] envelope_period_value_o
);

  // Register addresses
  localparam [3:0] ADDR_CONTROL = 4'h0;
  localparam [3:0] ADDR_NOTE_A = 4'h1;
  localparam [3:0] ADDR_CHANNEL_A_CONTROL = 4'h2;
  localparam [3:0] ADDR_NOTE_B = 4'h3;
  localparam [3:0] ADDR_CHANNEL_B_CONTROL = 4'h4;
  localparam [3:0] ADDR_VOLUME_AB = 4'h5;
  localparam [3:0] ADDR_NOISE_CONTROL = 4'h6;
  localparam [3:0] ADDR_ENVELOPE_CONTROL = 4'h7;
  localparam [3:0] ADDR_ENVELOPE_PERIOD = 4'h8;
  localparam [3:0] ADDR_STATUS = 4'h9;
  localparam [3:0] ADDR_ID = 4'ha;

  // ENVELOPE_CONTROL bits used now
  localparam integer ENVELOPE_MODE_LSB = 0;
  localparam integer ENVELOPE_MODE_MSB = 1;
  localparam integer ENVELOPE_ENABLE_A_BIT = 3;
  localparam integer ENVELOPE_ENABLE_B_BIT = 4;

  // Reset values for the stored registers
  localparam       DEFAULT_CONTROL_REG = 1'b0;
  localparam [6:0] DEFAULT_NOTE_REG = 7'h0f;
  localparam [5:0] DEFAULT_CHANNEL_CONTROL_REG = 6'h00;
  localparam [7:0] DEFAULT_VOLUME_AB_REG = 8'h00;
  localparam [3:0] DEFAULT_NOISE_CONTROL_REG = 4'h0;
  localparam [3:0] DEFAULT_ENVELOPE_CONTROL_REG = 4'h0;
  localparam [7:0] DEFAULT_ENVELOPE_PERIOD_REG = 8'h10;
  localparam [7:0] ID_REG_VALUE = 8'hdf;

  // Store only the bits that are used now
  reg       control_reg;
  reg [6:0] note_a_reg;
  reg [5:0] channel_a_control_reg;
  reg [6:0] note_b_reg;
  reg [5:0] channel_b_control_reg;
  reg [7:0] volume_ab_reg;
  reg [3:0] noise_control_reg;
  reg [3:0] envelope_control_reg;
  reg [7:0] envelope_period_reg;
  // STATUS[2] shows that one valid write has been accepted
  reg       write_seen_reg;

  // Build the full read values from the stored bits
  assign control_value_o = {7'b0000000, control_reg};
  assign note_a_value_o = {1'b0, note_a_reg};
  assign channel_a_control_value_o = {2'b00, channel_a_control_reg};
  assign note_b_value_o = {1'b0, note_b_reg};
  assign channel_b_control_value_o = {2'b00, channel_b_control_reg};
  assign volume_ab_value_o = volume_ab_reg;
  assign noise_control_value_o = {4'b0000, noise_control_reg};
  assign envelope_control_value_o = {
    3'b000,
    envelope_control_reg[3],
    envelope_control_reg[2],
    1'b0,
    envelope_control_reg[1:0]
  };
  assign envelope_period_value_o = envelope_period_reg;

  // Store one addressed register byte on each accepted write
  always @(posedge clk_i or negedge rst_ni) begin : registers_ff
    if (!rst_ni) begin
      control_reg <= DEFAULT_CONTROL_REG;
      note_a_reg <= DEFAULT_NOTE_REG;
      channel_a_control_reg <= DEFAULT_CHANNEL_CONTROL_REG;
      note_b_reg <= DEFAULT_NOTE_REG;
      channel_b_control_reg <= DEFAULT_CHANNEL_CONTROL_REG;
      volume_ab_reg <= DEFAULT_VOLUME_AB_REG;
      noise_control_reg <= DEFAULT_NOISE_CONTROL_REG;
      envelope_control_reg <= DEFAULT_ENVELOPE_CONTROL_REG;
      envelope_period_reg <= DEFAULT_ENVELOPE_PERIOD_REG;
      write_seen_reg <= 1'b0;
    end else begin
      if (write_enable_i) begin
        write_seen_reg <= 1'b1;

        case (write_address_i)
          ADDR_CONTROL: begin
            // Store CONTROL[0] and keep the pulse bit at 0
            control_reg <= write_data_i[0];

            if (write_data_i[1]) begin
              // CONTROL[1] clears the stored register state
              control_reg <= DEFAULT_CONTROL_REG;
              note_a_reg <= DEFAULT_NOTE_REG;
              channel_a_control_reg <= DEFAULT_CHANNEL_CONTROL_REG;
              note_b_reg <= DEFAULT_NOTE_REG;
              channel_b_control_reg <= DEFAULT_CHANNEL_CONTROL_REG;
              volume_ab_reg <= DEFAULT_VOLUME_AB_REG;
              noise_control_reg <= DEFAULT_NOISE_CONTROL_REG;
              envelope_control_reg <= DEFAULT_ENVELOPE_CONTROL_REG;
              envelope_period_reg <= DEFAULT_ENVELOPE_PERIOD_REG;
              write_seen_reg <= 1'b0;
            end
          end
          ADDR_NOTE_A: begin
            note_a_reg <= write_data_i[6:0];
          end
          ADDR_CHANNEL_A_CONTROL: begin
            channel_a_control_reg <= write_data_i[5:0];
          end
          ADDR_NOTE_B: begin
            note_b_reg <= write_data_i[6:0];
          end
          ADDR_CHANNEL_B_CONTROL: begin
            channel_b_control_reg <= write_data_i[5:0];
          end
          ADDR_VOLUME_AB: begin
            volume_ab_reg <= write_data_i;
          end
          ADDR_NOISE_CONTROL: begin
            noise_control_reg <= write_data_i[3:0];
          end
          ADDR_ENVELOPE_CONTROL: begin
            // Keep ENVELOPE_CONTROL[2] at 0
            envelope_control_reg <= {
              write_data_i[ENVELOPE_ENABLE_B_BIT],
              write_data_i[ENVELOPE_ENABLE_A_BIT],
              write_data_i[ENVELOPE_MODE_MSB:ENVELOPE_MODE_LSB]
            };
          end
          ADDR_ENVELOPE_PERIOD: begin
            envelope_period_reg <= write_data_i;
          end
          default: begin
          end
        endcase
      end
    end
  end

  // Return the byte selected by the read address
  always @* begin : read_data_comb
    read_data_o = 8'h00;

    case (read_address_i)
      ADDR_CONTROL: begin
        read_data_o = control_value_o;
      end
      ADDR_NOTE_A: begin
        read_data_o = note_a_value_o;
      end
      ADDR_CHANNEL_A_CONTROL: begin
        read_data_o = channel_a_control_value_o;
      end
      ADDR_NOTE_B: begin
        read_data_o = note_b_value_o;
      end
      ADDR_CHANNEL_B_CONTROL: begin
        read_data_o = channel_b_control_value_o;
      end
      ADDR_VOLUME_AB: begin
        read_data_o = volume_ab_reg;
      end
      ADDR_NOISE_CONTROL: begin
        read_data_o = noise_control_value_o;
      end
      ADDR_ENVELOPE_CONTROL: begin
        read_data_o = envelope_control_value_o;
      end
      ADDR_ENVELOPE_PERIOD: begin
        read_data_o = envelope_period_reg;
      end
      ADDR_STATUS: begin
        read_data_o = {5'b00000, write_seen_reg, 2'b00};
      end
      ADDR_ID: begin
        read_data_o = ID_REG_VALUE;
      end
      default: begin
        read_data_o = 8'h00;
      end
    endcase
  end

endmodule // register_file

`default_nettype wire
