// SPDX-License-Identifier: Apache-2.0
/*
 * File   : volume_control.v
 * Author : Peter Szentkuti
 *
 * Channel volume control
 *
 * Sets the output level of the input sample from either the fixed channel
 * volume or the shared envelope output. When envelope_enable_i is high,
 * envelope_level_i sets the sample level. Otherwise volume_level_i sets
 * the sample level. The 3 bit level code maps to eight output levels from
 * mute to full scale:
 *
 * output_level_code = envelope_level_i when envelope_enable_i = 1, else volume_level_i
 * sample_out_o = sample_in_i scaled by output_level_code
 */

`default_nettype none
`timescale 1ns / 1ps

module volume_control (
  input  wire signed [8:0] sample_in_i,
  input  wire [2:0]        volume_level_i,
  input  wire [2:0]        envelope_level_i,
  input  wire              envelope_enable_i,
  output reg  signed [9:0] sample_out_o
);

  // Use the shared envelope output level when envelope control is enabled,
  // else use the fixed channel volume level
  wire [2:0] output_level_code = envelope_enable_i ? envelope_level_i : volume_level_i;
  wire signed [9:0] sample_wide = {sample_in_i[8], sample_in_i};

  always @* begin : volume_scale_comb
    // Map the 3 bit output level code to one of eight sample output levels
    case (output_level_code)
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
