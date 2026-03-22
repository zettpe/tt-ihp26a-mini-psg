// SPDX-License-Identifier: Apache-2.0
/*
 * File        : waveform_generator.v
 * Author      : Peter Szentkuti
 * Description : Waveform generator for one tone channel
 *
 * Builds the selected wave from the upper phase bits
 */

`default_nettype none
`timescale 1ns / 1ps

// Builds one waveform sample from the upper phase bits
module waveform_generator (
  input  wire [7:0]        phase_view_i,
  input  wire [1:0]        waveform_select_i,
  output reg  signed [7:0] sample_out_o
);

  localparam [1:0] WAVE_SQUARE = 2'b00;
  localparam [1:0] WAVE_PULSE_25 = 2'b01;
  localparam [1:0] WAVE_SAW = 2'b10;
  localparam [1:0] WAVE_TRIANGLE = 2'b11;

  // Mirror the phase ramp to build the triangle shape
  wire [6:0] triangle_level =
      phase_view_i[7] ? ~phase_view_i[6:0] : phase_view_i[6:0];

  always @* begin : wave_comb
    case (waveform_select_i)
      WAVE_SQUARE: begin
        sample_out_o = phase_view_i[7] ? 8'sd96 : -8'sd96;
      end
      WAVE_PULSE_25: begin
        sample_out_o = (phase_view_i[7:6] == 2'b00) ? 8'sd96 : -8'sd96;
      end
      WAVE_SAW: begin
        sample_out_o = $signed(phase_view_i);
      end
      WAVE_TRIANGLE: begin
        sample_out_o = $signed({1'b0, triangle_level}) - 8'sd64;
      end
      default: begin
        sample_out_o = 8'sd0;
      end
    endcase
  end

endmodule // waveform_generator

`default_nettype wire
