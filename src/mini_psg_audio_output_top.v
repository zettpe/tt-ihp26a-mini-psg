// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_audio_output_top.v
 * Author      : Peter Szentkuti
 * Description : Level mix and audio output block
 *
 * Scales the channel source samples, mixes them, builds the 1 bit
 * audio output and drives the debug outputs
 */

`default_nettype none
`timescale 1ns / 1ps

// Scales mixes and sends the final audio and debug outputs
module mini_psg_audio_output_top (
  input  wire              clk_i,
  input  wire              rst_ni,
  input  wire              clear_enable_i,
  input  wire              audio_enable_i,
  input  wire              hard_mute_i,
  input  wire [7:0]        volume_ab_value_i,
  input  wire [3:0]        envelope_level_i,
  input  wire signed [8:0] channel_a_source_sample_i,
  input  wire signed [8:0] channel_b_source_sample_i,
  input  wire              channel_a_tone_enable_i,
  input  wire              channel_b_tone_enable_i,
  input  wire              channel_a_noise_enable_i,
  input  wire              channel_b_noise_enable_i,
  input  wire              channel_a_envelope_enable_i,
  input  wire              channel_b_envelope_enable_i,
  input  wire              shared_noise_bit_i,
  input  wire              channel_a_wave_debug_i,
  input  wire              channel_b_wave_debug_i,
  output wire              audio_o,
  output wire              channel_a_debug_o,
  output wire              channel_b_debug_o,
  output wire              noise_debug_o,
  output wire              envelope_debug_o,
  output wire              saturation_flag_o
);

  wire signed [9:0] channel_a_scaled_sample;
  wire signed [9:0] channel_b_scaled_sample;
  wire signed [8:0] mixed_sample;
  wire              audio_raw;

  // Apply the selected fixed level or envelope level
  volume_control volume_control_a_u (
    .sample_in_i       (channel_a_source_sample_i),
    .volume_level_i    (volume_ab_value_i[3:0]),
    .envelope_level_i  (envelope_level_i),
    .envelope_enable_i (channel_a_envelope_enable_i),
    .sample_out_o      (channel_a_scaled_sample)
  );

  volume_control volume_control_b_u (
    .sample_in_i       (channel_b_source_sample_i),
    .volume_level_i    (volume_ab_value_i[7:4]),
    .envelope_level_i  (envelope_level_i),
    .envelope_enable_i (channel_b_envelope_enable_i),
    .sample_out_o      (channel_b_scaled_sample)
  );

  // Mix both scaled channels and send the result to the 1 bit output block
  mixer mixer_u (
    .channel_a_sample_i(channel_a_scaled_sample),
    .channel_b_sample_i(channel_b_scaled_sample),
    .mixed_sample_o    (mixed_sample),
    .saturation_flag_o (saturation_flag_o)
  );

  dac_1bit dac_1bit_u (
    .clk_i         (clk_i),
    .rst_ni        (rst_ni),
    .clear_enable_i(clear_enable_i),
    .sample_in_i   (mixed_sample),
    .audio_o       (audio_raw)
  );

  // Show one simple debug view only when that source is active
  assign channel_a_debug_o = channel_a_tone_enable_i ?
      channel_a_wave_debug_i :
      1'b0;
  assign channel_b_debug_o = channel_b_tone_enable_i ?
      channel_b_wave_debug_i :
      1'b0;
  assign noise_debug_o = (channel_a_noise_enable_i || channel_b_noise_enable_i) ?
      shared_noise_bit_i : 1'b0;
  assign envelope_debug_o = audio_enable_i ?
      envelope_level_i[3] :
      1'b0;
  assign audio_o = (hard_mute_i || !audio_enable_i) ? 1'b0 : audio_raw;

endmodule // mini_psg_audio_output_top

`default_nettype wire
