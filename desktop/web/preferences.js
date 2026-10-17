export function resolvePreferences(...sources){
  const saved=Object.assign({},...sources),prefs={quality:'high',reduced:false,pinned:false,location_enabled:true,location_consent:'unknown',birthday_reminders_enabled:true,...saved};
  // Earlier releases inferred reduced motion from Windows. Migrate once to the requested full-effects default.
  if(saved.effects_default!=='full-1'){prefs.quality='high';prefs.reduced=false;}
  prefs.quality=prefs.quality==='low'?'low':'high';prefs.reduced=prefs.reduced===true;prefs.effects_default='full-1';
  prefs.location_enabled=prefs.location_enabled!==false;prefs.location_consent=['granted','denied'].includes(prefs.location_consent)?prefs.location_consent:'unknown';prefs.birthday_reminders_enabled=prefs.birthday_reminders_enabled!==false;
  return prefs;
}
