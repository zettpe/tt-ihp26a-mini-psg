// SPDX-License-Identifier: Apache-2.0
/*
 * File        : volume_control.v
 * Author      : Peter Szentkuti
 * Description : Sample level control
 *
 * Applies the fixed level or the shared envelope level with a
 * smaller set of shift and add steps
 */

`default_nettype none
`timescale 1ns / 1ps

// Applies the selected level to one sample stream
module volume_control (
  input  wire signed [8:0] sample_in_i,
  input  wire [2:0]        volume_level_i,
  input  wire [2:0]        envelope_level_i,
  input  wire              envelope_enable_i,
  output reg  signed [9:0] sample_out_o
);

  // Select the fixed level or the shared envelope level
  wire [2:0] level_value = envelope_enable_i ? envelope_level_i : volume_level_i;
  wire signed [9:0] sample_wide = {sample_in_i[8], sample_in_i};

  always @* begin : volume_scale_comb
    // Use a small set of coarse fixed levels
    case (level_value)
      3'h0:    sample_out_o = 10'sd0;
      3'h1:    sample_out_o = sample_wide >>> 3;
      3'h2:    sample_out_o = sample_wide >>> 2;
      3'h3:    sample_out_o = (sample_wide >>> 2) + (sample_wide >>> 3);
      3'h4:    sample_out_o = sample_wide >>> 1;
      3'h5:    sample_out_o = (sample_wide >>> 1) + (sample_wide >>> 3);
      3'h6:    sample_out_o = (sample_wide >>> 1) + (sample_wide >>> 2);
      3'h7:    sample_out_o = sample_wide;
      default: sample_out_o = 10'sd0;
    endcase
  end

endmodule // volume_control

`default_nettype wire
