import CaptionStylePresetPicker from "./CaptionStylePresetPicker";
import SectionHeading from "./SectionHeading";

function formatFileSize(bytes) {
  if (!bytes) {
    return "";
  }

  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function CaptionStyleSection({
  presets,
  selectedPresetId,
  form,
  files,
  result,
  error,
  loading,
  transcriptFormats,
  onPresetSelect,
  onFieldChange,
  onFileChange,
  onSubmit,
}) {
  return (
    <section className="stack">
      <SectionHeading
        title="Caption Style"
        description="Render a local video with styled burned-in captions using pycaps templates."
      />

      <CaptionStylePresetPicker
        presets={presets}
        selectedPresetId={selectedPresetId}
        onSelect={onPresetSelect}
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label className="upload-field">
            Input Video
            <input
              className="upload-input"
              type="file"
              name="input_video"
              accept="video/*"
              onChange={onFileChange}
              required
            />
            <span className="upload-summary">
              {files.input_video
                ? `${files.input_video.name} (${formatFileSize(files.input_video.size)})`
                : "Upload your source video file from this device."}
            </span>
          </label>

          <label className="upload-field">
            Transcript File
            <input
              className="upload-input"
              type="file"
              name="transcript"
              accept=".srt,.vtt,.json"
              onChange={onFileChange}
            />
            <span className="upload-summary">
              {files.transcript
                ? `${files.transcript.name} (${formatFileSize(files.transcript.size)})`
                : "Optional. Upload SRT, VTT, Whisper JSON, or pycaps JSON."}
            </span>
          </label>

          <p className="helper-text">
            Leave transcript empty if you want pycaps to transcribe automatically with
            Whisper after upload. Rendering may take longer on the first run.
          </p>

          <label>
            Transcript Format
            <select
              name="transcript_format"
              value={form.transcript_format}
              onChange={onFieldChange}
            >
              {transcriptFormats.map((format) => (
                <option key={format.value} value={format.value}>
                  {format.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Language Hint
            <input
              name="language_hint"
              value={form.language_hint}
              onChange={onFieldChange}
              placeholder="Optional: en or ms"
            />
          </label>

          <label>
            Style Name
            <input
              name="style_name"
              value={form.style_name}
              onChange={onFieldChange}
              placeholder="Minimalist"
              required
            />
          </label>

          <label>
            Template Name
            <input
              name="template_name"
              value={form.template_name}
              onChange={onFieldChange}
              placeholder="minimalist"
              required
            />
          </label>

          <label>
            Output Basename
            <input
              name="output_basename"
              value={form.output_basename}
              onChange={onFieldChange}
              placeholder="Optional: my-captioned-video"
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "Rendering..." : "Render captioned video"}
          </button>

          {error ? <p className="message error">{error}</p> : null}
        </form>

        <section className="panel result-panel caption-panel">
          <div className="result-header">
            <h2>Caption Result</h2>
            {result ? <span>{result.style_name}</span> : null}
          </div>

          {result ? (
            <div className="script-content">
              <video className="video-player" controls src={result.output_url}>
                Your browser does not support video playback.
              </video>
              <p className="script-event">Template: {result.template_name}</p>
              <p className="script-event">Output: {result.output_path}</p>
              <a href={result.output_url} target="_blank" rel="noreferrer">
                Open captioned video
              </a>
              <pre className="script-output">{result.command.join(" ")}</pre>
            </div>
          ) : (
            <div className="empty-state">
              <p>Your rendered captioned video will show up here.</p>
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
