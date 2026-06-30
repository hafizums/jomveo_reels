export default function VoiceMusicForm({ form, onChange, voiceStyles, musicPresets }) {
  return (
    <div className="create-form-grid">
      <label>
        Voice style
        <select name="voiceStyleId" value={form.voiceStyleId} onChange={onChange}>{voiceStyles.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      </label>
      <label>
        Background music
        <select name="musicPresetId" value={form.musicPresetId} onChange={onChange}>{musicPresets.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
      </label>
      <label className="create-field-wide">
        Music volume: {Math.round(form.musicVolume * 100)}%
        <input type="range" name="musicVolume" min="0" max="0.5" step="0.01" value={form.musicVolume} onChange={onChange} />
      </label>
    </div>
  );
}
