// SPDX-License-Identifier: Apache-2.0
/*
 * File        : volume_control.v
 * Author      : Peter Szentkuti
 * Description : Sample level control
 *
 * Applies the fixed level or the shared envelope level with shifts
 * and adds
 */

`default_nettype none
`timescale 1ns / 1ps

// Applies the selected level to one sample stream
module volume_control (
  input  wire signed [8:0] sample_in_i,
  input  wire [3:0]        volume_level_i,
  input  wire [3:0]        envelope_level_i,
  input  wire              envelope_enable_i,
  output reg  signed [9:0] sample_out_o
);

  // Select the fixed level or the shared envelope level
  wire [3:0] level_value = envelope_enable_i ? envelope_level_i : volume_level_i;
  wire signed [9:0] sample_wide = {sample_in_i[8], sample_in_i};

  always @* begin : volume_scale_comb
    // Use shift and add so the level control stays small
    case (level_value)
      4'h0:    sample_out_o = 10'sd0;
      4'h1:    sample_out_o = sample_wide >>> 4;
      4'h2:    sample_out_o = sample_wide >>> 3;
      4'h3:    sample_out_o = (sample_wide >>> 3) + (sample_wide >>> 4);
      4'h4:    sample_out_o = sample_wide >>> 2;
      4'h5:    sample_out_o = (sample_wide >>> 2) + (sample_wide >>> 4);
      4'h6:    sample_out_o = (sample_wide >>> 2) + (sample_wide >>> 3);
      4'h7:    sample_out_o = (sample_wide >>> 2) +
                              (sample_wide >>> 3) +
                              (sample_wide >>> 4);
      4'h8:    sample_out_o = sample_wide >>> 1;
      4'h9:    sample_out_o = (sample_wide >>> 1) + (sample_wide >>> 4);
      4'ha:    sample_out_o = (sample_wide >>> 1) + (sample_wide >>> 3);
      4'hb:    sample_out_o = (sample_wide >>> 1) +
                              (sample_wide >>> 3) +
                              (sample_wide >>> 4);
      4'hc:    sample_out_o = (sample_wide >>> 1) + (sample_wide >>> 2);
      4'hd:    sample_out_o = (sample_wide >>> 1) +
                              (sample_wide >>> 2) +
                              (sample_wide >>> 4);
      4'he:    sample_out_o = (sample_wide >>> 1) +
                              (sample_wide >>> 2) +
                              (sample_wide >>> 3);
      4'hf:    sample_out_o = sample_wide;
      default: sample_out_o = 10'sd0;
    endcase
  end

endmodule // volume_control

`default_nettype wire
