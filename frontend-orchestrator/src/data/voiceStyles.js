export const voiceStyles = [
  {
    id: "calm-narrator",
    name: "Calm Narrator",
    description: "A steady documentary-style read for history and dark storytelling.",
    voices: {
      Female: "Lily",
      Male: "Brian",
    },
  },
  {
    id: "midnight-whisper",
    name: "Midnight Whisper",
    description: "A softer dramatic delivery for eerie and unsettling stories.",
    voices: {
      Female: "Charlotte",
      Male: "Thomas",
    },
  },
  {
    id: "cold-case-host",
    name: "Cold Case Host",
    description: "A grounded investigative tone for true crime and disappearances.",
    voices: {
      Female: "Rachel",
      Male: "Daniel",
    },
  },
  {
    id: "war-archive",
    name: "War Archive",
    description: "A firm archival tone for military operations and Cold War stories.",
    voices: {
      Female: "Lily",
      Male: "Daniel",
    },
  },
  {
    id: "urgent-broadcast",
    name: "Urgent Broadcast",
    description: "A sharper, faster read for dramatic breaks and disaster recaps.",
    voices: {
      Female: "Jessica",
      Male: "Liam",
    },
  },
  {
    id: "stoic-guide",
    name: "Stoic Guide",
    description: "A measured reflective voice for philosophy and life lessons.",
    voices: {
      Female: "Sarah",
      Male: "George",
    },
  },
];

export const defaultVoiceStyle = voiceStyles[0];
export const supportedVoiceGenders = [
  { value: "Female", label: "Female" },
  { value: "Male", label: "Male" },
];

export function getVoiceId(style, gender) {
  return style.voices[gender] ?? style.voices.Female ?? Object.values(style.voices)[0];
}
