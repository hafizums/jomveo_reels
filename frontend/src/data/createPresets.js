export const createNichePresets = [
  { id: "malaysian-true-crime", title: "Malaysian true crime", truthMode: "factual", prompt: "Create factual Malaysian true-crime stories based on documented cases. Avoid inventing victims, suspects, evidence, or unresolved details." },
  { id: "scary-history", title: "Scary history", truthMode: "factual", prompt: "Create unsettling but factual history stories about disasters, disappearances, dangerous expeditions, political intrigue, and disturbing real events." },
  { id: "mythology", title: "Mythology", truthMode: "mythology", prompt: "Retell dramatic myths and legends while clearly presenting them as traditional stories rather than verified history." },
  { id: "school-gossip", title: "School gossip", truthMode: "inspirational", prompt: "Create playful fictional school-drama stories with anonymized characters, harmless misunderstandings, and no claims about real people." },
  { id: "dark-facts", title: "Dark facts", truthMode: "factual", prompt: "Create short factual stories around strange, unsettling, or little-known documented facts without exaggerating uncertain claims." },
  { id: "military-stories", title: "Military stories", truthMode: "factual", prompt: "Create factual military-history stories about strategy, survival, difficult decisions, and documented operations." },
  { id: "survival-stories", title: "Survival stories", truthMode: "factual", prompt: "Create factual survival stories focused on endurance, practical decisions, rescue efforts, and extraordinary real outcomes." },
  { id: "heists", title: "Heists", truthMode: "factual", prompt: "Create factual heist stories centered on planning, mistakes, investigations, and how documented cases ended." },
  { id: "custom", title: "Custom niche", truthMode: "factual", prompt: "" },
];

export const createLanguages = ["English", "Malay", "Mixed"];
export const createTones = ["scary", "documentary", "dramatic", "funny", "motivational"];
export const createDurations = [30, 45, 60, 75, 90];
