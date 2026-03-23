// SPDX-License-Identifier: Apache-2.0
/*
 * File   : mixer.v
 * Author : Peter Szentkuti
 *
 * Two channel mixer
 *
 * Adds both signed channel samples and limits the result to the 9 bit
 * signed output range. The block saturates the sum to -256 .. 255:
 *
 * sum_wide = channel_a_sample_i + channel_b_sample_i
 * mixed_sample_o = sum_wide, limited to -256 .. 255
 */

`default_nettype none

module mixer (
  input  wire signed [9:0] channel_a_sample_i,
  input  wire signed [9:0] channel_b_sample_i,
  output reg  signed [8:0] mixed_sample_o
);

  // Extend both inputs before adding so the sum keeps its sign
  wire signed [10:0] sum_wide =
      $signed({channel_a_sample_i[9], channel_a_sample_i}) +
      $signed({channel_b_sample_i[9], channel_b_sample_i});

  always @* begin : mix_output_comb
    // Limit the mix to the signed 9 bit output range
    if (sum_wide > 11'sd255) begin
      mixed_sample_o = 9'sd255;
    end else if (sum_wide < -11'sd256) begin
      mixed_sample_o = -9'sd256;
    end else begin
      mixed_sample_o = sum_wide[8:0];
    end
  end

endmodule // mixer
