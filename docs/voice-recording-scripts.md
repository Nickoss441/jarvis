# Voice Recording Scripts

Use this guide to create two custom Jarvis voices: one male and one female. The target is a clean, neutral assistant delivery that can later be tuned by your TTS provider.

## Recommended stack for Jarvis

For the best mix of speed, quality, and GPS-aware assistant behavior:

- STT: Deepgram streaming
- TTS: Cartesia for lowest latency, or ElevenLabs for highest custom voice quality
- Routing / ETA / traffic: Google Maps Routes API
- Weather: OpenWeather current + forecast APIs
- Location source: live phone GPS feed

If you prioritize voice quality over latency, choose ElevenLabs.
If you prioritize latency over voice quality, choose Cartesia.

## Recording requirements

- Record in a quiet room
- Use one microphone consistently
- Keep the same mouth-to-mic distance
- Avoid clipping, reverb, fan noise, and background music
- Save as WAV when possible
- Speak naturally, not like a character

Target per voice:

- 5 to 15 minutes minimum
- 50 to 100 short lines
- 20 to 30 medium lines
- 10 to 20 longer lines

## Male voice script

Read each line naturally.

1. Hello, I am ready.
2. Good morning. Here is your schedule.
3. The outside temperature is twelve degrees Celsius.
4. Light rain is expected in twenty minutes.
5. Wind speed is twenty kilometers per hour from the west.
6. Traffic is currently moderate on your usual route.
7. Estimated travel time to the office is twenty three minutes.
8. There is congestion on the ring road. I recommend an alternate route.
9. Your next meeting starts at nine thirty.
10. I drafted the reply and saved it for approval.
11. I found two route options with similar arrival times.
12. The fastest route is shorter by six minutes.
13. Rain intensity will increase after five o'clock.
14. You should leave in twelve minutes to arrive on time.
15. I can call ahead if you want me to confirm the reservation.
16. I found a delay on the train line into the city.
17. Indoor humidity is currently forty eight percent.
18. The package is scheduled to arrive before noon.
19. I paused the trade request because the policy limit was reached.
20. I am waiting for your approval before sending the message.

## Female voice script

Read each line naturally.

1. Hello, I am online.
2. Good afternoon. I have your updates ready.
3. The current temperature is eleven degrees Celsius.
4. There is a high chance of rain this evening.
5. Wind gusts may reach thirty kilometers per hour.
6. Traffic is building on the main route downtown.
7. Estimated arrival time to home is eighteen minutes.
8. I found a quicker route that avoids the motorway.
9. Your calendar is clear until two o'clock.
10. I saved the draft and queued it for review.
11. The weather should clear within the next hour.
12. Visibility is reduced because of steady rain.
13. I recommend leaving now to stay ahead of traffic.
14. The route through the city center is slower today.
15. I can read the forecast for the next three hours.
16. I found a nearby station with lighter congestion.
17. Your reminder has been scheduled for six fifteen.
18. I matched the merchant and verified the payment request.
19. I need confirmation before placing the call.
20. I am ready when you want the next update.

## Mixed utility lines for both voices

Use these for names, numbers, dates, and navigation phrasing.

1. Today is Friday, April twenty sixth, twenty twenty six.
2. The address is one hundred twenty three Market Street.
3. Turn left in two hundred meters.
4. Continue straight for one point five kilometers.
5. Arrival time is seven fourteen p.m.
6. The total cost is forty two euros and fifty cents.
7. Call John when you arrive.
8. Message Sarah that you are running five minutes late.
9. The battery is at sixty four percent.
10. Latitude fifty two point three six seven. Longitude four point nine zero four.

## Suggested environment variables

These are the voice-related settings Jarvis now supports.

```env
JARVIS_PHASE_VOICE=true
JARVIS_VOICE_WAKE_WORD=jarvis
JARVIS_VOICE_STT_PROVIDER=faster-whisper
JARVIS_VOICE_TTS_PROVIDER=elevenlabs
JARVIS_VOICE_TTS_MODEL=eleven_multilingual_v2
JARVIS_VOICE_TTS_DEFAULT_VOICE=male
JARVIS_VOICE_TTS_VOICE_ID_MALE=
JARVIS_VOICE_TTS_VOICE_ID_FEMALE=
ELEVENLABS_API_KEY=
```

## Recommended next integrations

1. Feed live phone GPS into Jarvis through a small webhook or shortcut.
2. Add a dedicated routes tool using Google Maps or Mapbox.
3. Add a weather tool that consumes GPS coordinates directly.
4. Use the male or female voice ID based on context or user preference.
