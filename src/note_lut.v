// SPDX-License-Identifier: Apache-2.0
/*
 * File   : note_lut.v
 * Author : Peter Szentkuti
 *
 * Note lookup table
 *
 * Maps the stored note code to a 23 bit phase step for a 25 MHz clock. The
 * lower four bits select one of ten tone codes, the upper three bits shift
 * that step by octave, and codes 10 to 15 return zero:
 *
 * tone_step = base step from note_value_i[3:0] when tone code is 0 to 9
 * phase_step_o = 0 when tone_step = 0, else tone_step * 2^note_value_i[6:4]
 */

`default_nettype none

module note_lut (
  input  wire [6:0]  note_value_i,
  output reg  [22:0] phase_step_o
);

  // Ten distinct base tone steps for one octave at 25 MHz with the
  // 23 bit phase path
  localparam [22:0] TONE_0_STEP = 23'd11;
  localparam [22:0] TONE_1_STEP = 23'd12;
  localparam [22:0] TONE_2_STEP = 23'd13;
  localparam [22:0] TONE_3_STEP = 23'd14;
  localparam [22:0] TONE_4_STEP = 23'd15;
  localparam [22:0] TONE_5_STEP = 23'd16;
  localparam [22:0] TONE_6_STEP = 23'd17;
  localparam [22:0] TONE_7_STEP = 23'd18;
  localparam [22:0] TONE_8_STEP = 23'd20;
  localparam [22:0] TONE_9_STEP = 23'd21;

  // Select the base tone step and shift it by octave
  wire [3:0] tone_code = note_value_i[3:0];
  wire [2:0] octave_value = note_value_i[6:4];
  reg  [22:0] tone_step;

  always @* begin : phase_step_comb
    tone_step = 23'd0;

    case (tone_code)
      4'd0:    tone_step = TONE_0_STEP;
      4'd1:    tone_step = TONE_1_STEP;
      4'd2:    tone_step = TONE_2_STEP;
      4'd3:    tone_step = TONE_3_STEP;
      4'd4:    tone_step = TONE_4_STEP;
      4'd5:    tone_step = TONE_5_STEP;
      4'd6:    tone_step = TONE_6_STEP;
      4'd7:    tone_step = TONE_7_STEP;
      4'd8:    tone_step = TONE_8_STEP;
      4'd9:    tone_step = TONE_9_STEP;
      default: tone_step = 23'd0;
    endcase

    // Tone codes 10 to 15 do not produce a tone
    if (tone_step == 23'd0) begin
      phase_step_o = 23'd0;
    end else begin
      phase_step_o = tone_step << octave_value;
    end
  end

endmodule // note_lut
