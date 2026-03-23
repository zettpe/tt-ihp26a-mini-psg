// SPDX-License-Identifier: Apache-2.0
/*
 * File        : envelope_generator.v
 * Author      : Peter Szentkuti
 * Description : Shared envelope generator
 *
 * Generates the shared 3 bit envelope level from the selected mode
 * and step period
 */

`default_nettype none
`timescale 1ns / 1ps

// Generates the shared 3 bit envelope level
module envelope_generator (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       clear_enable_i,
  input  wire       envelope_enable_i,
  input  wire       mode_select_i,
  input  wire [7:0] step_period_value_i,
  input  wire       restart_pulse_i,
  output reg  [2:0] envelope_level_o
);

  localparam ENVELOPE_SQUARE = 1'b0;

  reg  [7:0] counter_reg;
  reg        square_high_reg;
  // Treat a zero period as one clock step
  wire [7:0] step_period =
      (step_period_value_i == 8'd0) ? 8'd1 : step_period_value_i;

  always @(posedge clk_i or negedge rst_ni) begin : envelope_state_ff
    if (!rst_ni) begin
      counter_reg <= 8'd0;
      envelope_level_o <= 3'h7;
      square_high_reg <= 1'b1;
    end else if (clear_enable_i) begin
      counter_reg <= 8'd0;
      envelope_level_o <= 3'h7;
      square_high_reg <= 1'b1;
    end else if (!envelope_enable_i) begin
      counter_reg <= step_period - 8'd1;
      envelope_level_o <= 3'h7;
      square_high_reg <= 1'b1;
    end else if (restart_pulse_i) begin
      counter_reg <= step_period - 8'd1;
      envelope_level_o <= 3'h7;
      square_high_reg <= 1'b1;
    end else if (counter_reg != 8'd0) begin
      counter_reg <= counter_reg - 8'd1;
    end else begin
      counter_reg <= step_period - 8'd1;

      // Change the level only when one full step period has passed
      if (mode_select_i == ENVELOPE_SQUARE) begin
        square_high_reg <= ~square_high_reg;
        envelope_level_o <= square_high_reg ? 3'h0 : 3'h7;
      end else if (envelope_level_o == 3'd0) begin
        envelope_level_o <= 3'h7;
      end else begin
        envelope_level_o <= envelope_level_o - 3'd1;
      end
    end
  end

endmodule // envelope_generator

`default_nettype wire
