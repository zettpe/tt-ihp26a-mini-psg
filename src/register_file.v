// SPDX-License-Identifier: Apache-2.0
/*
 * File   : register_file.v
 * Author : Peter Szentkuti
 *
 * Register file
 *
 * Stores the live write register map and masks the unused bits on write.
 * The stored state covers CONTROL, NOTE_A, CHANNEL_A_CONTROL, NOTE_B,
 * CHANNEL_B_CONTROL, VOLUME_AB, ENVELOPE_CONTROL and ENVELOPE_PERIOD.
 */

`default_nettype none

module register_file (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       write_enable_i,
  input  wire [3:0] write_address_i,
  input  wire [7:0] write_data_i,
  output wire       control_value_o,
  output wire [6:0] note_a_value_o,
  output wire [4:0] channel_a_control_value_o,
  output wire [6:0] note_b_value_o,
  output wire [4:0] channel_b_control_value_o,
  output wire [5:0] volume_ab_value_o,
  output wire [2:0] envelope_control_value_o,
  output wire [7:0] envelope_period_value_o
);

  // Register addresses
  localparam [3:0] ADDR_CONTROL = 4'h0;
  localparam [3:0] ADDR_NOTE_A = 4'h1;
  localparam [3:0] ADDR_CHANNEL_A_CONTROL = 4'h2;
  localparam [3:0] ADDR_NOTE_B = 4'h3;
  localparam [3:0] ADDR_CHANNEL_B_CONTROL = 4'h4;
  localparam [3:0] ADDR_VOLUME_AB = 4'h5;
  localparam [3:0] ADDR_ENVELOPE_CONTROL = 4'h7;
  localparam [3:0] ADDR_ENVELOPE_PERIOD = 4'h8;

  // ENVELOPE_CONTROL write byte bit positions used now
  localparam integer ENVELOPE_MODE_BIT = 0;
  localparam integer ENVELOPE_ENABLE_A_BIT = 3;
  localparam integer ENVELOPE_ENABLE_B_BIT = 4;

  // Reset values for the stored registers
  localparam       DEFAULT_CONTROL_REG = 1'b0;
  localparam [6:0] DEFAULT_NOTE_REG = 7'h0f;
  localparam [4:0] DEFAULT_CHANNEL_CONTROL_REG = 5'h00;
  localparam [5:0] DEFAULT_VOLUME_AB_REG = 6'h00;
  localparam [2:0] DEFAULT_ENVELOPE_CONTROL_REG = 3'h0;
  localparam [7:0] DEFAULT_ENVELOPE_PERIOD_REG = 8'h10;

  // Store only the live bits from each register
  reg       control_reg;
  reg [6:0] note_a_reg;
  reg [4:0] channel_a_control_reg;
  reg [6:0] note_b_reg;
  reg [4:0] channel_b_control_reg;
  reg [5:0] volume_ab_reg;
  reg [2:0] envelope_control_reg;
  reg [7:0] envelope_period_reg;

  assign control_value_o = control_reg;
  assign note_a_value_o = note_a_reg;
  assign channel_a_control_value_o = channel_a_control_reg;
  assign note_b_value_o = note_b_reg;
  assign channel_b_control_value_o = channel_b_control_reg;
  assign volume_ab_value_o = volume_ab_reg;
  assign envelope_control_value_o = envelope_control_reg;
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
      envelope_control_reg <= DEFAULT_ENVELOPE_CONTROL_REG;
      envelope_period_reg <= DEFAULT_ENVELOPE_PERIOD_REG;
    end else begin
      if (write_enable_i) begin
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
              envelope_control_reg <= DEFAULT_ENVELOPE_CONTROL_REG;
              envelope_period_reg <= DEFAULT_ENVELOPE_PERIOD_REG;
            end
          end
          ADDR_NOTE_A: begin
            note_a_reg <= write_data_i[6:0];
          end
          ADDR_CHANNEL_A_CONTROL: begin
            // Keep waveform select, tone enable, envelope enable and gate enable
            channel_a_control_reg <= {
              write_data_i[5],
              write_data_i[4],
              write_data_i[2],
              write_data_i[1:0]
            };
          end
          ADDR_NOTE_B: begin
            note_b_reg <= write_data_i[6:0];
          end
          ADDR_CHANNEL_B_CONTROL: begin
            // Keep waveform select, tone enable, envelope enable and gate enable
            channel_b_control_reg <= {
              write_data_i[5],
              write_data_i[4],
              write_data_i[2],
              write_data_i[1:0]
            };
          end
          ADDR_VOLUME_AB: begin
            // Keep the two 3 bit channel volume fields
            volume_ab_reg <= {
              write_data_i[6:4],
              write_data_i[2:0]
            };
          end
          ADDR_ENVELOPE_CONTROL: begin
            // Store envelope mode and the two per-channel enable bits
            envelope_control_reg <= {
              write_data_i[ENVELOPE_ENABLE_B_BIT],
              write_data_i[ENVELOPE_ENABLE_A_BIT],
              write_data_i[ENVELOPE_MODE_BIT]
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

endmodule // register_file
