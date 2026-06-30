import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import VideoGeneratorSection from "./VideoGeneratorSection";

test("final video result shows the backend processing timeline", () => {
  render(
    <VideoGeneratorSection
      form={{ visual_source: "stills", duration_seconds: 60, aspect_ratio: "9:16", caption_style_id: "minimalist", music_volume: 0.16, video_quality: "low" }}
      result={{ output_url: "/generated/final.mp4", aspect_ratio: "9:16", width: 1080, height: 1920, duration_seconds: 60, scene_count: 8, visual_source: "stills", video_quality: "low", filtered_subtitle_cues: 1, processing_timings: [{ step: "merge_scenes", label: "Merge scene clips", duration_seconds: 1.234 }, { step: "transcription", label: "Transcribe audio", duration_seconds: 0.45 }, { step: "total", label: "Total processing time", duration_seconds: 8.5 }] }}
      error=""
      loading={false}
      hasScenes
      hasVoiceover
      hasMusic={false}
      sceneCount={8}
      hasAnimatedScenes={false}
      animatedSceneCount={0}
      captionStylePresets={[{ id: "minimalist", title: "Minimalist", description: "Clean", templateName: "minimalist" }]}
      durationOptions={[60]}
      aspectRatioOptions={[{ value: "9:16", label: "Vertical", resolution: "1080x1920" }]}
      qualityOptions={[{ value: "low", label: "Low — fastest" }, { value: "middle", label: "Balanced" }]}
      onFieldChange={vi.fn()}
      onSubmit={vi.fn()}
    />,
  );

  expect(screen.getByRole("heading", { name: "Processing time" })).toBeVisible();
  expect(screen.getByRole("combobox", { name: /Video Quality/ })).toHaveValue("low");
  expect(screen.getByText("Quality: low")).toBeVisible();
  expect(screen.getByText("Merge scene clips")).toBeVisible();
  expect(screen.getByText("1.23 s")).toBeVisible();
  expect(screen.getByText("450 ms")).toBeVisible();
  expect(screen.getByText("8.50 s")).toBeVisible();
  expect(screen.getByText("Removed 1 suspicious trailing subtitle cue.")).toBeVisible();
});
