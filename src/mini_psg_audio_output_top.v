// SPDX-License-Identifier: Apache-2.0
/*
 * File   : mini_psg_audio_output_top.v
 * Author : Peter Szentkuti
 *
 * Audio output path wrapper
 *
 * Applies the selected channel volume or the shared envelope level, mixes
 * both channels and drives the 1 bit audio output. Hard mute is
 * synchronized into clk_i before it clears the DAC state or gates the
 * output pin.
 */

`default_nettype none

module mini_psg_audio_output_top (
  input  wire              clk_i,
  input  wire              rst_ni,
  input  wire              clear_enable_i,
  input  wire              audio_enable_i,
  input  wire              hard_mute_i,
  input  wire [5:0]        volume_ab_value_i,
  input  wire [2:0]        envelope_level_i,
  input  wire signed [8:0] channel_a_source_sample_i,
  input  wire signed [8:0] channel_b_source_sample_i,
  input  wire              channel_a_envelope_enable_i,
  input  wire              channel_b_envelope_enable_i,
  output wire              audio_o
);

  wire signed [9:0] channel_a_scaled_sample;
  wire signed [9:0] channel_b_scaled_sample;
  wire signed [8:0] mixed_sample;
  wire              audio_raw;
  reg  [1:0]        hard_mute_sync_q;
  wire              hard_mute_sync = hard_mute_sync_q[1];
  wire              dac_clear = clear_enable_i || !audio_enable_i || hard_mute_sync;

  // Synchronize hard mute so the DAC clear path and the top audio pin both
  // stay inside the clk_i domain
  always @(posedge clk_i or negedge rst_ni) begin : hard_mute_sync_ff
    if (!rst_ni) begin
      hard_mute_sync_q <= 2'b00;
    end else begin
      hard_mute_sync_q <= {hard_mute_sync_q[0], hard_mute_i};
    end
  end

  // Scale each channel with fixed volume or the shared envelope level
  volume_control volume_control_a_u (
    .sample_in_i       (channel_a_source_sample_i),
    .volume_level_i    (volume_ab_value_i[2:0]),
    .envelope_level_i  (envelope_level_i),
    .envelope_enable_i (channel_a_envelope_enable_i),
    .sample_out_o      (channel_a_scaled_sample)
  );

  volume_control volume_control_b_u (
    .sample_in_i       (channel_b_source_sample_i),
    .volume_level_i    (volume_ab_value_i[5:3]),
    .envelope_level_i  (envelope_level_i),
    .envelope_enable_i (channel_b_envelope_enable_i),
    .sample_out_o      (channel_b_scaled_sample)
  );

  // Mix both scaled channels and convert the result to 1 bit audio
  mixer mixer_u (
    .channel_a_sample_i(channel_a_scaled_sample),
    .channel_b_sample_i(channel_b_scaled_sample),
    .mixed_sample_o    (mixed_sample)
  );

  // Clear the DAC on global clear, audio disable or synchronized hard mute
  dac_1bit dac_1bit_u (
    .clk_i         (clk_i),
    .rst_ni        (rst_ni),
    .clear_enable_i(dac_clear),
    .sample_in_i   (mixed_sample),
    .audio_o       (audio_raw)
  );

  // Gate the output pin with synchronized hard mute and audio enable
  assign audio_o = (hard_mute_sync || !audio_enable_i) ? 1'b0 : audio_raw;

endmodule // mini_psg_audio_output_top
