// SPDX-License-Identifier: Apache-2.0
/*
 * File        : phase_accumulator.v
 * Author      : Peter Szentkuti
 * Description : Phase accumulator for one tone channel
 *
 * Adds the phase step on each enabled clock edge and clears the phase
 * when reset or clear is active
 */

`default_nettype none
`timescale 1ns / 1ps

// Stores the running phase for one tone channel
module phase_accumulator (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        clear_enable_i,
  input  wire        advance_en_i,
  input  wire        gate_en_i,
  input  wire [23:0] phase_step_i,
  output reg  [23:0] phase_value_o
);

  // Clear the phase on reset or clear and advance it only when both enables are high
  always @(posedge clk_i or negedge rst_ni) begin : phase_value_ff
    if (!rst_ni) begin
      phase_value_o <= 24'd0;
    end else if (clear_enable_i) begin
      phase_value_o <= 24'd0;
    end else if (advance_en_i && gate_en_i) begin
      phase_value_o <= phase_value_o + phase_step_i;
    end
  end

endmodule // phase_accumulator

`default_nettype wire
