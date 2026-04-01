from google import genai
from pathlib import Path
from PIL import Image
import json
import re

IMAGE = Image.open("harvansh.jpg") # harvansh image for reference

GENESIS_LIST = ["horror", "fantasy", "history", "science fiction", "comedy"] # list of genesis points
CONVERSATION_LOG = Path("conversation_log.json")
CONVERSATION_LENGTH = 2 # number of turns in the conversation

""" HELPER FUNCTIONS """

def _load_conversation() -> dict:
    if CONVERSATION_LOG.exists():
        with CONVERSATION_LOG.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"conversation": [], "conversation_length": 0}

def _save_conversation(log: dict) -> None:
    with CONVERSATION_LOG.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def list_to_string(conversation: list) -> str:
    transcript_lines = []

    for entry in conversation:
        # Safely extract the text, providing a default if the key is missing
        god_text = entry.get("god", "[No response]")
        you_text = entry.get("you", "[No response]")
        
        # Format the strings and add them to our list
        transcript_lines.append(f"God: {god_text}")
        transcript_lines.append(f"You: {you_text}")
        transcript_lines.append("") # Blank line for spacing

    final_string = "\n".join(transcript_lines)
    return final_string

def response_parser(response): #assume input is response.text
    # Extract everything between ## ... ##
    matches = re.findall(r"##(.*?)##", response, re.DOTALL)

    if len(matches) == 3:
        story = matches[0].strip()
        options_raw = matches[1].strip()
        description = matches[2].strip()

        # Split options
        options = [opt.strip() for opt in options_raw.split("|")]

        return [story, options, description]
    
    elif len(matches) == 2:
        story = matches[0].strip()
        description = matches[1].strip()
        return [story, description]
    else:
        raise ValueError("Invalid format: Expected 2 or 3 sections enclosed in ## ... ##")

""" PROMPT BUILDERS """

def genesis_prompt(genesis): # based on the genesis point, generates the initial prompt
    return f"You are to write out a dynamic conversation with me. \
             The conversation must be based on a story of the following genre: {genesis}. \
             The text you return has 3 parts, separate them by new lines. The parts are: \
             1 - Write the beginning of the conversation in 100 words or less. \
                 Start with a ## and end with a ## \
             2 - Write 3 options each 5 words or less giving the user an option to move the conversation foward to a new place. \
                 Start with a ##, write all options in one line, separate each by a | and end with a ## \
             3 - Write a short description of the person you are pretending to be in the conversation in 10 words or less. No grammer, just raw description. \
                 Start with a ## and end with a ## \
             Do not write anything else, just the 3 sections."

def __vansh_generator_prompt(description): # based on the character description, generates a prompt to create an image of the character
    return f"Generate an image with the man in the attached image as the subject. \
             The man should have the following characteristics: {description}. \
             He should be facing the camera. "

def conversation_prompt(conversation_history, god_quote, option): # generates the response from god based on the previous conversation history, the last thing god said and the option the user chose to proceed further
    return f"You are conversing with a user in a dynamic storytelling scenario. \
             The conversation history so far is as follows: {conversation_history}. \
             Your last message was: {god_quote}. \
             The user has responded with the following option to proceed further: {option}. \
             Based on this information, write the next part of the conversation. \
             The text you return has 3 parts, separate them by new lines. The parts are: \
             1 - Write the next part of the conversation in 100 words or less. \
                 Change the tone and style to reflect a new person talking. \
                 Start with a ## and end with a ## \
             2 - Write 3 options each 5 words or less giving the user an option to move the conversation foward to a new person. \
                 Start with a ##, write all options in one line, separate each by a | and end with a ## \
             3 - Write a short description of the person you are pretending to be in the conversation in 10 words or less. No grammer, just raw description. \
                 Start with a ## and end with a ## \
             Do not write anything else, just the 3 sections."

def conversation_end_prompt(conversation_history, god_quote, option): # ending prompt, separate since no need for options
    return f"You are conversing with a user in a dynamic storytelling scenario. \
             The conversation history so far is as follows: {conversation_history}. \
             Your last message was: {god_quote}. \
             The user has responded with the following option to proceed further: {option}. \
             Based on this information, write the conclusion of the conversation in 100 words or less. \
             Change the tone and style to reflect a new person talking. \
             The text you return has 2 parts, separate them by new lines. The parts are: \
             1 - Write the conclusion of the conversation in 100 words or less. \
                 Start with a ## and end with a ## \
             2 - Write a short description of the person you are pretending to be in the conversation in 10 words or less. No grammer, just raw description. \
                 Start with a ## and end with a ## \
             Do not write anything else, just the 2 sections."

""" MAIN CONVERSATION LOOP """

def conversation_loop():
    
    client = genai.Client()

    """ GENESIS"""

    print("Please choose a genesis option:")
    for index, item in enumerate(GENESIS_LIST, 1): # Starts counting at 1 instead of 0 for a more natural menu
        print(f"{index}. {item}")  
      
    genesis = None
    while True: #Create a loop to get and validate the user's input
        user_input = input("\nEnter the number of your choice: ")
        try:
            choice_number = int(user_input) # Convert their input into an integer
            if 1 <= choice_number <= len(GENESIS_LIST): # Check if the number is actually on the menu (between 1 and 5)
                genesis = GENESIS_LIST[choice_number - 1]
                break
            else:
                print(f"Invalid choice. Please pick a number between 1 and {len(GENESIS_LIST)}.")
                
        except ValueError:
            # This catches the error if they typed a word like "banana" instead of "2"
            print("Invalid input. Please type a number.")

    print(f"\nOption Chosen: {genesis}")

    conversation_log = _load_conversation()

    prompt = genesis_prompt(genesis)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=[prompt],
        config=genai.types.GenerateContentConfig(
            response_modalities=["TEXT"],
            candidate_count=1,
        )
    )

    god_quote = ""
    options = []
    description = ""

    [god_quote, options, description] = response_parser(response.text)

    i = 0

    while i < CONVERSATION_LENGTH:
        i += 1
        
        """ Generate a new image based on the current description and image """

        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[__vansh_generator_prompt(description), IMAGE],
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                candidate_count=1,
                image_config=genai.types.ImageConfig(
                    image_size="512",
                    aspect_ratio="1:1"
                )
            )
        )

        for part in response.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = part.as_image()
                image.save(f"generated_image_{i}.png")


        """ BEGIN LOOP """

        print(f"\nGod: {god_quote}\n")
        print("Your options:")

        # optional
        # print(f"(Description of current character: {description})")

        for index, item in enumerate(options, 1):
            print(f"{index}. {item}")

        
        option = None
        while True: #Create a loop to get and validate the user's input
            user_input = input("\nEnter the number of your choice: ")
            
            try:
                choice_number = int(user_input)
                if 1 <= choice_number <= len(options):
                    option = options[choice_number - 1]
                    break
                else:
                    print(f"Invalid choice. Please pick a number between 1 and {len(options)}.")
                    
            except ValueError:
                # This catches the error if they typed a word like "banana" instead of "2"
                print("Invalid input. Please type a number.")

        print(f"\nOption Chosen: {option}")

        prompt = conversation_prompt(conversation_history=list_to_string(conversation_log.get("conversation", [])), god_quote=god_quote, option=option)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=[prompt],
            config=genai.types.GenerateContentConfig(
                response_modalities=["TEXT"],
                candidate_count=1,
            )
        )

        [god_quote, options, description] = response_parser(response.text)

        conversation_log["conversation"].append({"god": god_quote, "you": option})
        conversation_log["conversation_length"] = conversation_log["conversation_length"] + 1
        _save_conversation(conversation_log)
    
    """ ENDING """

    prompt = conversation_end_prompt(conversation_history=list_to_string(conversation_log.get("conversation", [])), god_quote=god_quote, option=option)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=[prompt],
        config=genai.types.GenerateContentConfig(
            response_modalities=["TEXT"],
            candidate_count=1,
        )
    )
    [god_quote, description] = response_parser(response.text)
    conversation_log["conversation"].append({"god": god_quote, "you": "FINISH"})
    conversation_log["conversation_length"] = conversation_log["conversation_length"] + 1
    _save_conversation(conversation_log)

    response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[__vansh_generator_prompt(description), IMAGE],
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                candidate_count=1,
                image_config=genai.types.ImageConfig(
                    image_size="512",
                    aspect_ratio="1:1"
                )
            )
        )

    for part in response.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = part.as_image()
            image.save(f"generated_image_finish.png")

    print(f"\nGod: {god_quote}\n")
    print(f"(Description of final character: {description})")
    print("The End.")

if __name__ == "__main__":
    conversation_loop()



