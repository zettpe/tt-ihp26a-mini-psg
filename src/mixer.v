// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mixer.v
 * Author      : Peter Szentkuti
 * Description : Two channel mixer
 *
 * Adds both channel levels and limits the result to the 9 bit audio range
 */

`default_nettype none
`timescale 1ns / 1ps

// Adds both channel samples and limits the result to the audio range
module mixer (
  input  wire signed [9:0] channel_a_sample_i,
  input  wire signed [9:0] channel_b_sample_i,
  output reg  signed [8:0] mixed_sample_o
);

  wire signed [10:0] sum_wide =
      $signed({channel_a_sample_i[9], channel_a_sample_i}) +
      $signed({channel_b_sample_i[9], channel_b_sample_i});

  always @* begin : mix_output_comb
    // Limit the mix to the 9 bit range used by the 1 bit output block
    if (sum_wide > 11'sd255) begin
      mixed_sample_o = 9'sd255;
    end else if (sum_wide < -11'sd256) begin
      mixed_sample_o = -9'sd256;
    end else begin
      mixed_sample_o = sum_wide[8:0];
    end
  end

endmodule // mixer

`default_nettype wire
