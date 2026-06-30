export const buildScriptJobPayload=form=>({...form});
export const buildVoiceoverJobPayload=form=>form.text?.trim()?{...form}:null;
export const buildMusicJobPayload=form=>({...form});
export const buildArtJobPayload=form=>({...form});
export function buildSceneSequenceJobPayload({scriptResult,artForm}) { return scriptResult?.script?{script:scriptResult.script,title:scriptResult.title,event_name:scriptResult.event_name,duration_seconds:scriptResult.duration_seconds,planner_model:"openai/gpt-5.4-mini",style_name:artForm.style_name,art_direction:artForm.art_direction,model:artForm.model,enable_safety_checker:artForm.enable_safety_checker}:null; }
export function buildSceneAnimationJobPayload({artSceneResult,sceneAnimationForm}) { return artSceneResult?.scenes?.length?{duration:sceneAnimationForm.duration,negative_prompt:sceneAnimationForm.negative_prompt,model:"wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",scenes:artSceneResult.scenes.map(scene=>({scene_number:scene.scene_number,image_url:scene.image_url,motion_prompt:scene.motion_prompt}))}:null; }
export function buildVideoJobPayload({scriptResult,artSceneResult,sceneAnimationResult,voiceResult,musicResult,videoForm,captionStylePresets,defaultCaptionStylePreset}) { if(!artSceneResult?.scenes?.length||!voiceResult?.audio_url)return null;const preset=captionStylePresets.find(item=>item.id===videoForm.caption_style_id)??defaultCaptionStylePreset;return{title:scriptResult?.title||"Generated video",duration_seconds:videoForm.duration_seconds,aspect_ratio:videoForm.aspect_ratio,visual_source:videoForm.visual_source,image_urls:artSceneResult.scenes.map(scene=>scene.image_url),video_urls:sceneAnimationResult?.scenes?.map(scene=>scene.video_url)||[],voiceover_url:voiceResult.audio_url,music_url:musicResult?.audio_urls?.[0]||"",music_volume:videoForm.music_volume,caption_template:preset.templateName,caption_style_name:preset.title,language_hint:scriptResult?.language==="Malay"?"ms":"en",whisper_prompt:scriptResult?.script||""}; }
export function resolveQueueConfiguration({activeTab,requestedKind,scriptForm,voiceForm,musicForm,artForm,scriptResult,artSceneResult,sceneAnimationForm,sceneAnimationResult,voiceResult,musicResult,videoForm,captionStylePresets,defaultCaptionStylePreset}) {
  if(activeTab==="scripts")return["scripts",buildScriptJobPayload(scriptForm)];
  if(activeTab==="voiceover"){const payload=buildVoiceoverJobPayload(voiceForm);return payload?["voiceovers",payload]:null;}
  if(activeTab==="music")return["background-music",buildMusicJobPayload(musicForm)];
  if(activeTab==="art")return requestedKind==="art-style/scenes"?(p=>p?["art-style/scenes",p]:null)(buildSceneSequenceJobPayload({scriptResult,artForm})):["art-style",buildArtJobPayload(artForm)];
  if(activeTab==="animation"){const payload=buildSceneAnimationJobPayload({artSceneResult,sceneAnimationForm});return payload?["scene-animations",payload]:null;}
  if(activeTab==="video"){const payload=buildVideoJobPayload({scriptResult,artSceneResult,sceneAnimationResult,voiceResult,musicResult,videoForm,captionStylePresets,defaultCaptionStylePreset});return payload?["videos",payload]:null;}
  return null;
}
