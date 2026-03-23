// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_audio_generator_top.v
 * Author      : Peter Szentkuti
 * Description : Tone noise and envelope block
 *
 * Builds the channel source samples and the envelope level from
 * the stored register values
 */

`default_nettype none
`timescale 1ns / 1ps

// Builds the tone noise and envelope source signals
module mini_psg_audio_generator_top (
  input  wire              clk_i,
  input  wire              rst_ni,
  input  wire              clear_enable_i,
  input  wire              audio_enable_i,
  input  wire [7:0]        note_a_value_i,
  input  wire [7:0]        channel_a_control_value_i,
  input  wire [7:0]        note_b_value_i,
  input  wire [7:0]        channel_b_control_value_i,
  input  wire [7:0]        noise_control_value_i,
  input  wire [7:0]        envelope_control_value_i,
  input  wire [7:0]        envelope_period_value_i,
  input  wire              envelope_restart_pulse_i,
  output wire [3:0]        envelope_level_o,
  output wire              channel_a_envelope_enable_o,
  output wire              channel_b_envelope_enable_o,
  output wire signed [8:0] channel_a_source_sample_o,
  output wire signed [8:0] channel_b_source_sample_o
);

  // CHANNEL_CONTROL bit fields
  localparam integer CHANNEL_CONTROL_WAVEFORM_LSB = 0;
  localparam integer CHANNEL_CONTROL_WAVEFORM_MSB = 1;
  localparam integer CHANNEL_CONTROL_TONE_ENABLE_BIT = 2;
  localparam integer CHANNEL_CONTROL_NOISE_ENABLE_BIT = 3;
  localparam integer CHANNEL_CONTROL_ENVELOPE_ENABLE_BIT = 4;
  localparam integer CHANNEL_CONTROL_GATE_ENABLE_BIT = 5;

  // NOISE_CONTROL bit fields
  localparam integer NOISE_CONTROL_ENABLE_BIT = 0;
  localparam integer NOISE_CONTROL_RATE_LSB = 1;
  localparam integer NOISE_CONTROL_RATE_MSB = 3;

  // ENVELOPE_CONTROL bit fields
  localparam integer ENVELOPE_CONTROL_MODE_LSB = 0;
  localparam integer ENVELOPE_CONTROL_MODE_MSB = 1;
  localparam integer ENVELOPE_CONTROL_ENABLE_A_BIT = 3;
  localparam integer ENVELOPE_CONTROL_ENABLE_B_BIT = 4;

  wire [23:0]       channel_a_phase_step;
  wire [23:0]       channel_b_phase_step;
  wire [23:0]       channel_a_phase_value;
  wire [23:0]       channel_b_phase_value;
  wire [7:0]        channel_a_phase_view = channel_a_phase_value[23:16];
  wire [7:0]        channel_b_phase_view = channel_b_phase_value[23:16];
  wire signed [7:0] channel_a_wave_sample;
  wire signed [7:0] channel_b_wave_sample;
  wire              shared_noise_bit;
  wire signed [7:0] shared_noise_sample;
  wire signed [7:0] channel_a_tone_sample;
  wire signed [7:0] channel_b_tone_sample;
  wire signed [7:0] channel_a_noise_sample;
  wire signed [7:0] channel_b_noise_sample;
  wire              channel_a_gate_on;
  wire              channel_b_gate_on;
  wire              noise_on;
  wire              channel_a_tone_enable;
  wire              channel_b_tone_enable;
  wire              channel_a_noise_enable;
  wire              channel_b_noise_enable;

  // Gate and enable bits decide which source parts are live
  assign channel_a_gate_on = audio_enable_i &&
      channel_a_control_value_i[CHANNEL_CONTROL_GATE_ENABLE_BIT];
  assign channel_b_gate_on = audio_enable_i &&
      channel_b_control_value_i[CHANNEL_CONTROL_GATE_ENABLE_BIT];
  assign noise_on = audio_enable_i &&
      noise_control_value_i[NOISE_CONTROL_ENABLE_BIT];

  assign channel_a_tone_enable = channel_a_gate_on &&
      channel_a_control_value_i[CHANNEL_CONTROL_TONE_ENABLE_BIT] &&
      (channel_a_phase_step != 24'd0);
  assign channel_b_tone_enable = channel_b_gate_on &&
      channel_b_control_value_i[CHANNEL_CONTROL_TONE_ENABLE_BIT] &&
      (channel_b_phase_step != 24'd0);
  assign channel_a_noise_enable = channel_a_gate_on &&
      channel_a_control_value_i[CHANNEL_CONTROL_NOISE_ENABLE_BIT] &&
      noise_on;
  assign channel_b_noise_enable = channel_b_gate_on &&
      channel_b_control_value_i[CHANNEL_CONTROL_NOISE_ENABLE_BIT] &&
      noise_on;
  assign channel_a_envelope_enable_o =
      channel_a_control_value_i[CHANNEL_CONTROL_ENVELOPE_ENABLE_BIT] &&
      envelope_control_value_i[ENVELOPE_CONTROL_ENABLE_A_BIT];
  assign channel_b_envelope_enable_o =
      channel_b_control_value_i[CHANNEL_CONTROL_ENVELOPE_ENABLE_BIT] &&
      envelope_control_value_i[ENVELOPE_CONTROL_ENABLE_B_BIT];

  // Convert the stored note values to phase steps
  note_lut note_lut_a_u (
    .note_value_i(note_a_value_i),
    .phase_step_o(channel_a_phase_step)
  );

  note_lut note_lut_b_u (
    .note_value_i(note_b_value_i),
    .phase_step_o(channel_b_phase_step)
  );

  // Run one phase accumulator per tone channel
  phase_accumulator phase_accumulator_a_u (
    .clk_i         (clk_i),
    .rst_ni        (rst_ni),
    .clear_enable_i(clear_enable_i),
    .advance_en_i  (audio_enable_i &&
                    channel_a_control_value_i[CHANNEL_CONTROL_TONE_ENABLE_BIT]),
    .gate_en_i     (channel_a_control_value_i[CHANNEL_CONTROL_GATE_ENABLE_BIT]),
    .phase_step_i  (channel_a_phase_step),
    .phase_value_o (channel_a_phase_value)
  );

  phase_accumulator phase_accumulator_b_u (
    .clk_i         (clk_i),
    .rst_ni        (rst_ni),
    .clear_enable_i(clear_enable_i),
    .advance_en_i  (audio_enable_i &&
                    channel_b_control_value_i[CHANNEL_CONTROL_TONE_ENABLE_BIT]),
    .gate_en_i     (channel_b_control_value_i[CHANNEL_CONTROL_GATE_ENABLE_BIT]),
    .phase_step_i  (channel_b_phase_step),
    .phase_value_o (channel_b_phase_value)
  );

  // Build the selected waveform from the upper phase bits
  waveform_generator waveform_generator_a_u (
    .phase_view_i      (channel_a_phase_view),
    .waveform_select_i (channel_a_control_value_i[
        CHANNEL_CONTROL_WAVEFORM_MSB:CHANNEL_CONTROL_WAVEFORM_LSB]),
    .sample_out_o      (channel_a_wave_sample)
  );

  waveform_generator waveform_generator_b_u (
    .phase_view_i      (channel_b_phase_view),
    .waveform_select_i (channel_b_control_value_i[
        CHANNEL_CONTROL_WAVEFORM_MSB:CHANNEL_CONTROL_WAVEFORM_LSB]),
    .sample_out_o      (channel_b_wave_sample)
  );

  // Build the shared noise bit and the shared envelope level
  noise_generator noise_generator_u (
    .clk_i         (clk_i),
    .rst_ni        (rst_ni),
    .clear_enable_i(clear_enable_i),
    .noise_enable_i(noise_on),
    .rate_select_i (noise_control_value_i[
        NOISE_CONTROL_RATE_MSB:NOISE_CONTROL_RATE_LSB]),
    .noise_bit_o   (shared_noise_bit),
    .noise_sample_o(shared_noise_sample)
  );

  envelope_generator envelope_generator_u (
    .clk_i               (clk_i),
    .rst_ni              (rst_ni),
    .clear_enable_i      (clear_enable_i),
    .envelope_enable_i   (audio_enable_i),
    .mode_select_i       (envelope_control_value_i[
        ENVELOPE_CONTROL_MODE_MSB:ENVELOPE_CONTROL_MODE_LSB]),
    .step_period_value_i (envelope_period_value_i),
    .restart_pulse_i     (envelope_restart_pulse_i),
    .envelope_level_o    (envelope_level_o)
  );

  // Add the enabled tone and noise parts for each channel
  assign channel_a_tone_sample =
      channel_a_tone_enable ? channel_a_wave_sample : 8'sd0;
  assign channel_b_tone_sample =
      channel_b_tone_enable ? channel_b_wave_sample : 8'sd0;
  assign channel_a_noise_sample =
      channel_a_noise_enable ? shared_noise_sample : 8'sd0;
  assign channel_b_noise_sample =
      channel_b_noise_enable ? shared_noise_sample : 8'sd0;
  assign channel_a_source_sample_o =
      $signed({channel_a_tone_sample[7], channel_a_tone_sample}) +
      $signed({channel_a_noise_sample[7], channel_a_noise_sample});
  assign channel_b_source_sample_o =
      $signed({channel_b_tone_sample[7], channel_b_tone_sample}) +
      $signed({channel_b_noise_sample[7], channel_b_noise_sample});

  // These stored bits are not used now
  wire unused_control_bits = &{
    channel_a_control_value_i[7:6],
    channel_b_control_value_i[7:6],
    noise_control_value_i[7:4],
    envelope_control_value_i[7:5],
    envelope_control_value_i[2],
    shared_noise_bit,
    channel_a_phase_value[15:0],
    channel_b_phase_value[15:0],
    1'b0
  };

endmodule // mini_psg_audio_generator_top

`default_nettype wire
