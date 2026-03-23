// SPDX-License-Identifier: Apache-2.0
/*
 * File   : note_lut.v
 * Author : Peter Szentkuti
 *
 * Note lookup table
 *
 * Maps the stored note code to a 23 bit phase step for a 25 MHz clock. The
 * lower four bits select the semitone table, the upper three bits shift
 * that step by octave, and rest or unmapped note codes return zero:
 *
 * base_step = semitone step from note_value_i[3:0]
 * phase_step_o = 0 when base_step = 0, else base_step * 2^note_value_i[6:4]
 */

`default_nettype none

module note_lut (
  input  wire [6:0]  note_value_i,
  output reg  [22:0] phase_step_o
);

  // Base semitone steps for one octave at 25 MHz
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

  // Select the semitone step and shift it by octave
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

    // Note index 15 is the rest code, and unmapped note codes also return 0
    if ((note_index == 4'd15) || (base_step == 23'd0)) begin
      phase_step_o = 23'd0;
    end else begin
      phase_step_o = base_step << octave_value;
    end
  end

endmodule // note_lut
