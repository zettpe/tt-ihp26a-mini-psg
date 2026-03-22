// SPDX-License-Identifier: Apache-2.0
/*
 * File        : envelope_generator.v
 * Author      : Peter Szentkuti
 * Description : Shared envelope generator
 *
 * Generates the shared 4 bit envelope level from the selected mode
 * and step period
 */

`default_nettype none
`timescale 1ns / 1ps

// Generates the shared 4 bit envelope level
module envelope_generator (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       clear_enable_i,
  input  wire       envelope_enable_i,
  input  wire [1:0] mode_select_i,
  input  wire [7:0] step_period_value_i,
  input  wire       restart_pulse_i,
  output reg  [3:0] envelope_level_o
);

  localparam [1:0] ENVELOPE_HOLD_HIGH = 2'b00;
  localparam [1:0] ENVELOPE_DECAY = 2'b01;
  localparam [1:0] ENVELOPE_RISE_THEN_FALL = 2'b10;
  localparam [1:0] ENVELOPE_LOOP = 2'b11;

  reg  [7:0] counter_reg;
  reg        rise_reg;
  // Treat a zero period as one clock step
  wire [7:0] step_period =
      (step_period_value_i == 8'd0) ? 8'd1 : step_period_value_i;

  always @(posedge clk_i or negedge rst_ni) begin : envelope_state_ff
    if (!rst_ni) begin
      counter_reg <= 8'd0;
      envelope_level_o <= 4'hf;
      rise_reg <= 1'b1;
    end else if (clear_enable_i) begin
      counter_reg <= 8'd0;
      envelope_level_o <= 4'hf;
      rise_reg <= 1'b1;
    end else if (!envelope_enable_i) begin
      counter_reg <= step_period - 8'd1;
      envelope_level_o <= 4'hf;
      rise_reg <= 1'b1;
    end else if (restart_pulse_i) begin
      // Restart from the mode start level
      counter_reg <= step_period - 8'd1;

      case (mode_select_i)
        ENVELOPE_HOLD_HIGH: begin
          envelope_level_o <= 4'hf;
          rise_reg <= 1'b1;
        end
        ENVELOPE_DECAY: begin
          envelope_level_o <= 4'hf;
          rise_reg <= 1'b0;
        end
        ENVELOPE_RISE_THEN_FALL: begin
          envelope_level_o <= 4'h0;
          rise_reg <= 1'b1;
        end
        ENVELOPE_LOOP: begin
          envelope_level_o <= 4'h0;
          rise_reg <= 1'b1;
        end
        default: begin
          envelope_level_o <= 4'hf;
          rise_reg <= 1'b1;
        end
      endcase
    end else if (mode_select_i == ENVELOPE_HOLD_HIGH) begin
      // Hold the top level when the hold mode is selected
      counter_reg <= step_period - 8'd1;
      envelope_level_o <= 4'hf;
      rise_reg <= 1'b1;
    end else if (counter_reg != 8'd0) begin
      counter_reg <= counter_reg - 8'd1;
    end else begin
      counter_reg <= step_period - 8'd1;

      // Change the level only when one full step period has passed
      case (mode_select_i)
        ENVELOPE_DECAY: begin
          if (envelope_level_o != 4'd0) begin
            envelope_level_o <= envelope_level_o - 4'd1;
          end
        end
        ENVELOPE_RISE_THEN_FALL: begin
          if (rise_reg) begin
            if (envelope_level_o == 4'hf) begin
              rise_reg <= 1'b0;
            end else begin
              envelope_level_o <= envelope_level_o + 4'd1;
            end
          end else if (envelope_level_o != 4'd0) begin
            envelope_level_o <= envelope_level_o - 4'd1;
          end
        end
        ENVELOPE_LOOP: begin
          if (rise_reg) begin
            if (envelope_level_o == 4'hf) begin
              rise_reg <= 1'b0;
              envelope_level_o <= 4'he;
            end else begin
              envelope_level_o <= envelope_level_o + 4'd1;
            end
          end else if (envelope_level_o == 4'd0) begin
            rise_reg <= 1'b1;
            envelope_level_o <= 4'd1;
          end else begin
            envelope_level_o <= envelope_level_o - 4'd1;
          end
        end
        default: begin
          envelope_level_o <= 4'hf;
          rise_reg <= 1'b1;
        end
      endcase
    end
  end

endmodule // envelope_generator

`default_nettype wire
