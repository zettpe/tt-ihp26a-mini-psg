// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_top.v
 * Author      : Peter Szentkuti
 * Description : Project top
 */

`default_nettype none
`timescale 1ns / 1ps

module mini_psg_top (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       spi_cs_ni,
  input  wire       spi_sck_i,
  input  wire       spi_mosi_i,
  input  wire       hard_mute_i,
  output wire       spi_miso_o,
  output wire       spi_miso_oe_o,
  output wire       audio_o,
  output wire       channel_a_debug_o,
  output wire       channel_b_debug_o,
  output wire       noise_debug_o,
  output wire       envelope_debug_o,
  output wire       saturation_flag_o,
  output wire       spi_access_pulse_o,
  output wire       spi_read_active_o
);

  wire       clear_enable;
  wire       audio_enable;
  wire [7:0] note_a_value;
  wire [7:0] channel_a_control_value;
  wire [7:0] note_b_value;
  wire [7:0] channel_b_control_value;
  wire [7:0] volume_ab_value;
  wire [7:0] noise_control_value;
  wire [7:0] envelope_control_value;
  wire [7:0] envelope_period_value;
  wire       envelope_restart_pulse;

  mini_psg_control_top mini_psg_control_top_u (
    .clk_i                    (clk_i),
    .rst_ni                   (rst_ni),
    .spi_cs_ni                (spi_cs_ni),
    .spi_sck_i                (spi_sck_i),
    .spi_mosi_i               (spi_mosi_i),
    .spi_miso_o               (spi_miso_o),
    .spi_miso_oe_o            (spi_miso_oe_o),
    .spi_access_pulse_o       (spi_access_pulse_o),
    .spi_read_active_o        (spi_read_active_o),
    .clear_enable_o           (clear_enable),
    .audio_enable_o           (audio_enable),
    .note_a_value_o           (note_a_value),
    .channel_a_control_value_o(channel_a_control_value),
    .note_b_value_o           (note_b_value),
    .channel_b_control_value_o(channel_b_control_value),
    .volume_ab_value_o        (volume_ab_value),
    .noise_control_value_o    (noise_control_value),
    .envelope_control_value_o (envelope_control_value),
    .envelope_period_value_o  (envelope_period_value),
    .envelope_restart_pulse_o (envelope_restart_pulse)
  );

  mini_psg_audio_top mini_psg_audio_top_u (
    .clk_i                     (clk_i),
    .rst_ni                    (rst_ni),
    .clear_enable_i            (clear_enable),
    .audio_enable_i            (audio_enable),
    .hard_mute_i               (hard_mute_i),
    .note_a_value_i            (note_a_value),
    .channel_a_control_value_i (channel_a_control_value),
    .note_b_value_i            (note_b_value),
    .channel_b_control_value_i (channel_b_control_value),
    .volume_ab_value_i         (volume_ab_value),
    .noise_control_value_i     (noise_control_value),
    .envelope_control_value_i  (envelope_control_value),
    .envelope_period_value_i   (envelope_period_value),
    .envelope_restart_pulse_i  (envelope_restart_pulse),
    .audio_o                   (audio_o),
    .channel_a_debug_o         (channel_a_debug_o),
    .channel_b_debug_o         (channel_b_debug_o),
    .noise_debug_o             (noise_debug_o),
    .envelope_debug_o          (envelope_debug_o),
    .saturation_flag_o         (saturation_flag_o)
  );

endmodule // mini_psg_top

`default_nettype wire
