// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_audio_top.v
 * Author      : Peter Szentkuti
 * Description : Audio block
 *
 * Connects the tone noise and envelope signals to the level control,
 * mixer and 1 bit audio output block
 */

`default_nettype none
`timescale 1ns / 1ps

// Connects the audio signal block and the audio output block
module mini_psg_audio_top (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       clear_enable_i,
  input  wire       audio_enable_i,
  input  wire       hard_mute_i,
  input  wire [7:0] note_a_value_i,
  input  wire [7:0] channel_a_control_value_i,
  input  wire [7:0] note_b_value_i,
  input  wire [7:0] channel_b_control_value_i,
  input  wire [7:0] volume_ab_value_i,
  input  wire [7:0] noise_control_value_i,
  input  wire [7:0] envelope_control_value_i,
  input  wire [7:0] envelope_period_value_i,
  input  wire       envelope_restart_pulse_i,
  output wire       audio_o,
  output wire       channel_a_debug_o,
  output wire       channel_b_debug_o,
  output wire       noise_debug_o,
  output wire       envelope_debug_o,
  output wire       saturation_flag_o
);

  wire              shared_noise_bit;
  wire [3:0]        envelope_level;
  wire signed [8:0] channel_a_source_sample;
  wire signed [8:0] channel_b_source_sample;
  wire              channel_a_tone_enable;
  wire              channel_b_tone_enable;
  wire              channel_a_noise_enable;
  wire              channel_b_noise_enable;
  wire              channel_a_envelope_enable;
  wire              channel_b_envelope_enable;
  wire              channel_a_wave_debug_raw;
  wire              channel_b_wave_debug_raw;

  // Generate the raw channel samples and debug signals
  mini_psg_audio_generator_top mini_psg_audio_generator_top_u (
    .clk_i                      (clk_i),
    .rst_ni                     (rst_ni),
    .clear_enable_i             (clear_enable_i),
    .audio_enable_i             (audio_enable_i),
    .note_a_value_i             (note_a_value_i),
    .channel_a_control_value_i  (channel_a_control_value_i),
    .note_b_value_i             (note_b_value_i),
    .channel_b_control_value_i  (channel_b_control_value_i),
    .noise_control_value_i      (noise_control_value_i),
    .envelope_control_value_i   (envelope_control_value_i),
    .envelope_period_value_i    (envelope_period_value_i),
    .envelope_restart_pulse_i   (envelope_restart_pulse_i),
    .shared_noise_bit_o         (shared_noise_bit),
    .envelope_level_o           (envelope_level),
    .channel_a_tone_enable_o    (channel_a_tone_enable),
    .channel_b_tone_enable_o    (channel_b_tone_enable),
    .channel_a_noise_enable_o   (channel_a_noise_enable),
    .channel_b_noise_enable_o   (channel_b_noise_enable),
    .channel_a_envelope_enable_o(channel_a_envelope_enable),
    .channel_b_envelope_enable_o(channel_b_envelope_enable),
    .channel_a_source_sample_o  (channel_a_source_sample),
    .channel_b_source_sample_o  (channel_b_source_sample),
    .channel_a_wave_debug_o     (channel_a_wave_debug_raw),
    .channel_b_wave_debug_o     (channel_b_wave_debug_raw)
  );

  // Scale mix and send the audio and debug outputs
  mini_psg_audio_output_top mini_psg_audio_output_top_u (
    .clk_i                      (clk_i),
    .rst_ni                     (rst_ni),
    .clear_enable_i             (clear_enable_i),
    .audio_enable_i             (audio_enable_i),
    .hard_mute_i                (hard_mute_i),
    .volume_ab_value_i          (volume_ab_value_i),
    .envelope_level_i           (envelope_level),
    .channel_a_source_sample_i  (channel_a_source_sample),
    .channel_b_source_sample_i  (channel_b_source_sample),
    .channel_a_tone_enable_i    (channel_a_tone_enable),
    .channel_b_tone_enable_i    (channel_b_tone_enable),
    .channel_a_noise_enable_i   (channel_a_noise_enable),
    .channel_b_noise_enable_i   (channel_b_noise_enable),
    .channel_a_envelope_enable_i(channel_a_envelope_enable),
    .channel_b_envelope_enable_i(channel_b_envelope_enable),
    .shared_noise_bit_i         (shared_noise_bit),
    .channel_a_wave_debug_i     (channel_a_wave_debug_raw),
    .channel_b_wave_debug_i     (channel_b_wave_debug_raw),
    .audio_o                    (audio_o),
    .channel_a_debug_o          (channel_a_debug_o),
    .channel_b_debug_o          (channel_b_debug_o),
    .noise_debug_o              (noise_debug_o),
    .envelope_debug_o           (envelope_debug_o),
    .saturation_flag_o          (saturation_flag_o)
  );

endmodule // mini_psg_audio_top

`default_nettype wire
