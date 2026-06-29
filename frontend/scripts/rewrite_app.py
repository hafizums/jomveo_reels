import os
import re

app_jsx_path = r"c:\Users\froxt\Downloads\jomveo\frontend\src\App.jsx"

with open(app_jsx_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import
content = content.replace('import SceneAnimationSection from "./components/SceneAnimationSection";',
                          'import SceneAnimationSection from "./components/SceneAnimationSection";\nimport JobProgress from "./components/JobProgress";')

# Replace loading states
content = re.sub(r'const \[(\w+)Loading\], set\w+Loading\] = useState\(false\);', 
                 lambda m: f'const [{m.group(1)}Job, set{m.group(1).capitalize()}Job] = useState(null);', 
                 content)

# Add pollJob and cancelJob
helper_funcs = """
  const pollJob = async (jobId, setJob, setResult, setError, onSuccess) => {
    let polling = true;
    while (polling) {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error?.message || "Polling failed");
        
        setJob(data);

        if (data.status === "completed") {
          setResult(data.result);
          setJob(null);
          polling = false;
          if (onSuccess) onSuccess(data.result);
        } else if (data.status === "failed" || data.status === "cancelled") {
          setError(data.error?.message || `Job ${data.status}`);
          setJob(null);
          polling = false;
        } else {
          await new Promise((r) => setTimeout(r, 1500));
        }
      } catch (err) {
        setError(err.message);
        setJob(null);
        polling = false;
      }
    }
  };

  const cancelJob = async (jobId, setJob) => {
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" });
      setJob((current) => (current ? { ...current, status: "cancelling" } : null));
    } catch (err) {
      console.error("Failed to cancel job:", err);
    }
  };

  const selectedPreset =
"""
content = content.replace('  const selectedPreset =', helper_funcs)

# Update handlers
def rewrite_handler(name, endpoint, job_state, result_state, error_state, extra_success=""):
    pattern = rf'  const {name} = async \(.*?\) => {{.*?finally {{\s*set{job_state.capitalize().replace("Job", "Loading")}\(false\);\s*}}\s*}};'
    
    body = f"""  const {name} = async (event) => {{
    if (event) event.preventDefault();
    set{error_state.capitalize()}("");
    set{job_state.capitalize()}({{ status: "queued", progress_current: 0, progress_total: 100 }});
"""
    if "Caption" in name:
        # Caption is synchronous, mock job
        body = f"""  const {name} = async (event) => {{
    event.preventDefault();
    set{error_state.capitalize()}("");
    
    if (!captionFiles.input_video) {{
      setCaptionError("Please upload a video file before rendering captions.");
      return;
    }}

    set{job_state.capitalize()}({{ status: "running", progress_current: 0, progress_total: 0 }});

    try {{
      const body = new FormData();
      body.append("input_video", captionFiles.input_video);
      body.append("template_name", captionForm.template_name);
      body.append("transcript_format", captionForm.transcript_format);
      body.append("language_hint", captionForm.language_hint);
      body.append("style_name", captionForm.style_name);
      body.append("output_basename", captionForm.output_basename);

      if (captionFiles.transcript) {{
        body.append("transcript", captionFiles.transcript);
      }}

      const response = await fetch("/api/caption-style/generate", {{
        method: "POST",
        body,
      }});

      const data = await response.json();
      if (!response.ok) {{
        throw new Error(data.detail || "Caption style request failed");
      }}

      set{result_state.capitalize()}(data);
    }} catch (submitError) {{
      set{error_state.capitalize()}(submitError.message);
    }} finally {{
      set{job_state.capitalize()}(null);
    }}
  }};"""
    else:
        # Add special pre-checks
        prechecks = ""
        if name == "handleArtScenesSubmit":
            prechecks = """
    if (!scriptResult?.script) {
      setArtError("Generate a script before creating a scene sequence.");
      setArtSceneJob(null);
      return;
    }
"""
        elif name == "handleSceneAnimationSubmit":
            prechecks = """
    if (!artSceneResult?.scenes?.length) {
      setSceneAnimationError("Generate an art scene sequence before animating it.");
      setSceneAnimationJob(null);
      return;
    }
"""
        elif name == "handleVideoSubmit":
            prechecks = """
    const hasSelectedVisuals =
      videoForm.visual_source === "animated"
        ? Boolean(sceneAnimationResult?.scenes?.length)
        : Boolean(artSceneResult?.scenes?.length);
    if (!hasSelectedVisuals || !voiceResult?.audio_url) {
      setVideoError("Generate the selected visual source and a voiceover before creating the video.");
      setVideoJob(null);
      return;
    }
"""

        body += prechecks
        body += f"""
    try {{
      const response = await fetch("{endpoint}", {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json",
        }},"""
        
        if name == "handleArtScenesSubmit":
            body += """
        body: JSON.stringify({
          script: scriptResult.script,
          title: scriptResult.title,
          event_name: scriptResult.event_name,
          duration_seconds: scriptResult.duration_seconds,
          planner_model: "openai/gpt-5.4-mini",
          style_name: artForm.style_name,
          art_direction: artForm.art_direction,
          model: artForm.model,
          enable_safety_checker: artForm.enable_safety_checker,
        }),
      });"""
        elif name == "handleSceneAnimationSubmit":
            body += """
        body: JSON.stringify({
          duration: sceneAnimationForm.duration,
          negative_prompt: sceneAnimationForm.negative_prompt,
          model: "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
          scenes: artSceneResult.scenes.map((scene) => ({
            scene_number: scene.scene_number,
            image_url: scene.image_url,
            motion_prompt: scene.motion_prompt,
          })),
        }),
      });"""
        elif name == "handleVideoSubmit":
            body += """
        body: JSON.stringify({
          title: scriptResult?.title || "Generated video",
          duration_seconds: videoForm.duration_seconds,
          aspect_ratio: videoForm.aspect_ratio,
          visual_source: videoForm.visual_source,
          image_urls: artSceneResult.scenes.map((scene) => scene.image_url),
          video_urls: sceneAnimationResult?.scenes?.map((scene) => scene.video_url) || [],
          voiceover_url: voiceResult.audio_url,
          music_url: musicResult?.audio_urls?.[0] || "",
          music_volume: videoForm.music_volume,
          caption_template: captionStylePresets.find((preset) => preset.id === videoForm.caption_style_id)?.templateName || "Hype",
          caption_style_name: captionStylePresets.find((preset) => preset.id === videoForm.caption_style_id)?.title || "Hype",
          language_hint: scriptResult?.language === "Malay" ? "ms" : "en",
        }),
      });"""
        elif name == "handleScriptSubmit":
            body += f"""
        body: JSON.stringify({job_state.replace("Job", "Form")}),
      }});"""
        else:
            body += f"""
        body: JSON.stringify({job_state.replace("Job", "Form")}),
      }});"""

        body += f"""
      const data = await response.json();
      if (!response.ok) {{
        throw new Error(data.detail || "Request failed");
      }}
"""
        if name == "handleArtSubmit":
            extra_success = "setArtSceneResult(null);\n"
        elif name == "handleArtScenesSubmit":
            extra_success = "setArtResult(null);\nsetSceneAnimationResult(null);\n"
            
        on_success = f"""(result) => {{
          {extra_success}
        }}"""
        if name == "handleScriptSubmit":
            on_success = """(result) => {
          setVideoForm((current) => ({
            ...current,
            duration_seconds: result.duration_seconds,
          }));
        }"""
        elif extra_success == "":
            on_success = "undefined"

        body += f"""
      set{job_state.capitalize()}(data);
      pollJob(data.job_id, set{job_state.capitalize()}, set{result_state.capitalize()}, set{error_state.capitalize()}, {on_success});
    }} catch (submitError) {{
      set{error_state.capitalize()}(submitError.message);
      set{job_state.capitalize()}(null);
    }}
  }};"""
    
    content = re.sub(rf'  const {name} = async \(.*?\) => {{.*?finally {{\s*set{job_state.capitalize().replace("Job", "Loading")}\(.*?\);\s*}}\s*}};', body, content, flags=re.DOTALL)

content = re.sub(r'const \[(\w+)Loading\], set\w+Loading\] = useState\(false\);', 
                 lambda m: f'const [{m.group(1)}Job, set{m.group(1).capitalize()}Job] = useState(null);', 
                 content)

# Fix loading passing to components
# loading={scriptLoading} -> job={scriptJob} onCancel={() => cancelJob(scriptJob.job_id, setScriptJob)}
def fix_props(section, job_name):
    global content
    content = re.sub(rf'loading={{{job_name.replace("Job", "Loading")}}}', f'job={{{job_name}}}\n            onCancel={{() => cancelJob({job_name}?.job_id, set{job_name.capitalize()})}}', content)

fix_props("ScriptGeneratorSection", "scriptJob")
fix_props("VoiceoverGeneratorSection", "voiceJob")
fix_props("BackgroundMusicSection", "musicJob")
fix_props("ArtStyleSection", "artJob")
fix_props("CaptionStyleSection", "captionJob")
fix_props("VideoGeneratorSection", "videoJob")

# Special cases
content = re.sub(r'sceneLoading={artSceneLoading}', 'sceneJob={artSceneJob}\n            onSceneCancel={() => cancelJob(artSceneJob?.job_id, setArtSceneJob)}', content)
content = re.sub(r'loading={sceneAnimationLoading}', 'job={sceneAnimationJob}\n            onCancel={() => cancelJob(sceneAnimationJob?.job_id, setSceneAnimationJob)}', content)


with open(app_jsx_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Rewrite script completed.")
