export default function VisualStyleForm({ form, onChange, artStyles, captionStyles, aspectRatios, qualityOptions }) {
  return (
    <div className="create-form-grid">
      <label>
        Art style
        <select name="artStyleId" value={form.artStyleId} onChange={onChange}>{artStyles.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
      </label>
      <label>
        Visual source
        <select name="visualSource" value={form.visualSource} onChange={onChange}><option value="stills">Still scenes</option><option value="animated">Animated scenes</option></select>
      </label>
      <label>
        Aspect ratio
        <select name="aspectRatio" value={form.aspectRatio} onChange={onChange}>{aspectRatios.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      </label>
      <label>
        Video quality
        <select name="videoQuality" value={form.videoQuality} onChange={onChange}>{qualityOptions.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      </label>
      <label>
        Caption style
        <select name="captionStyleId" value={form.captionStyleId} onChange={onChange}>{captionStyles.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
      </label>
    </div>
  );
}
