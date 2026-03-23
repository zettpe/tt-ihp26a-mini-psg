// SPDX-License-Identifier: Apache-2.0
/*
 * File        : note_lut.v
 * Author      : Peter Szentkuti
 * Description : Note to phase step lookup
 *
 * Maps the stored note value to a 23 bit phase step for a 25 MHz clock
 */

`default_nettype none
`timescale 1ns / 1ps

// Maps the stored note value to a phase step
module note_lut (
  input  wire [6:0]  note_value_i,
  output reg  [22:0] phase_step_o
);

  localparam [22:0] SEMITONE_0_STEP  = 23'd11;
  localparam [22:0] SEMITONE_1_STEP  = 23'd12;
  localparam [22:0] SEMITONE_2_STEP  = 23'd13;
  localparam [22:0] SEMITONE_3_STEP  = 23'd13;
  localparam [22:0] SEMITONE_4_STEP  = 23'd14;
  localparam [22:0] SEMITONE_5_STEP  = 23'd15;
  localparam [22:0] SEMITONE_6_STEP  = 23'd16;
  localparam [22:0] SEMITONE_7_STEP  = 23'd17;
  localparam [22:0] SEMITONE_8_STEP  = 23'd18;
  localparam [22:0] SEMITONE_9_STEP  = 23'd19;
  localparam [22:0] SEMITONE_10_STEP = 23'd20;
  localparam [22:0] SEMITONE_11_STEP = 23'd21;

  // Keep one octave table and shift it for the selected octave
  wire [3:0] note_index = note_value_i[3:0];
  wire [2:0] octave_value = note_value_i[6:4];
  reg  [22:0] base_step;

  always @* begin : phase_step_comb
    base_step = 23'd0;

    case (note_index)
      4'd0:    base_step = SEMITONE_0_STEP;
      4'd1:    base_step = SEMITONE_1_STEP;
      4'd2:    base_step = SEMITONE_2_STEP;
      4'd3:    base_step = SEMITONE_3_STEP;
      4'd4:    base_step = SEMITONE_4_STEP;
      4'd5:    base_step = SEMITONE_5_STEP;
      4'd6:    base_step = SEMITONE_6_STEP;
      4'd7:    base_step = SEMITONE_7_STEP;
      4'd8:    base_step = SEMITONE_8_STEP;
      4'd9:    base_step = SEMITONE_9_STEP;
      4'd10:   base_step = SEMITONE_10_STEP;
      4'd11:   base_step = SEMITONE_11_STEP;
      default: base_step = 23'd0;
    endcase

    // Note index 15 is the rest code in this build
    if ((note_index == 4'd15) || (base_step == 23'd0)) begin
      phase_step_o = 23'd0;
    end else begin
      phase_step_o = base_step << octave_value;
    end
  end

endmodule // note_lut

`default_nettype wire
