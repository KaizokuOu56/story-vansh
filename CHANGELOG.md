# v0.0.1
Goal is to build a basic interface where I talk to program, program accordingly generates a new scenario and gives options, based on options it generates a new vansh variant.
Tells more about the scenario, maybe text from vansh variant, then new options and cycle repeats.

## Progress
- Added an API call logger to monitor calls and costs
- Updated gemini_logger to handle gemini-2.5-flash-image too, but this model sucks.
  Cannot retain facial data. Stick with 3.1-flash-image-preview for now.
- Finished main.py; choose 1 of 5 genesis options to start conversation,
                    generate images and text with options to continue conversation,
                    continue until convo limit reached

## Goals for next version
- Minor improvements so next will be **v0.0.2**
- Clean up code
- Add logger after every api call
- Current convo logging kinda shit, need to improve
- MAYBE add the __-vansh feature? Gonna need to summarise the description into one
  word, another api call? Maybe include summary request in earlier call itself 

---