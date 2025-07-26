import openai


import json
import os


class Creds:
    def __init__(self):
        self.api_json_path = "api_key.json"

    def init_json(self):
        content = {"open_ai_api_key": "placeholder"}

        with open(self.api_json_path, "w") as f:
            json.dump(content, f)

    def load_api_key(self):
        if not os.path.exists(self.api_json_path):
            self.init_json()
            print(
                f"API key file not found at {self.api_json_path}. Please run init_json() first."
            )
            return False

        with open(self.api_json_path, "r") as f:
            data = json.load(f)
            api_key = data.get("open_ai_api_key", False)
            if not api_key or api_key == "placeholder":
                print("API key is not set. Please update the api_key.json file.")
                return False
            return api_key




class PostMetadataGenerator:
    def __init__(self):
        #store system prompt here
        self.system_prompt = """
    You are a YouTube Shorts metadata generator for Reddit storytime content. Your job is to take Reddit-style story text and create:

    1. A **clickbait-style YouTube Shorts TITLE** (under 70 characters)
    2. A **fun, SEO-optimized DESCRIPTION** including hashtags like #redditstories #minecraftparkour #storytime #shorts

    Always keep the tone engaging but safe for YouTube, with no profanity.
    Only return the result in this format:
    ---
    TITLE: <catchy title here>

    DESCRIPTION:
    <2-4 lines of description>
    <Hashtags>
    ---
    """
        
        #init client with creds from file
        creds = Creds()
        api_key = creds.load_api_key()
        if not api_key:
            raise ValueError(
                "Open AI API key is not set. Please update the api_key.json file.\nThis is necessary for youtube post metadata generation."
            )
        self.client = openai.OpenAI(api_key=api_key)


    def output_to_dict(self, output_string):
        """
            TITLE: My Mom's Scary Mood Swings Caught Me Off Guard at Costco!

            DESCRIPTION:
            Experience the rollercoaster of 
        """
        
        try:
            title_part, description_part = output_string.split('DESCRIPTION:')
            title_part = title_part.replace('TITLE:', '').strip()
            description_part = description_part.strip()
        except:
            return False

        return {
            "title": title_part,
            "description": description_part
        }

    def generate_youtube_metadata(self, content):
        user_prompt = f"Here is the Reddit story content:\n\n{content}"

        response = self.client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        output_string =  response.choices[0].message.content
        data_dict = self.output_to_dict(output_string)
        if data_dict is False:
            print('[!] Fatal error: this openai output was not in the expected format!')
            return False
        
        return data_dict


# Example usage:
if __name__ == "__main__":
    content = "The switch up is crazy and scary.\nI was just in Costco with my mother and she was putting on a performance; smiling, being friendly and trying to be funny but I knew she was putting on a show. My life is honestly so much easier when she is not abusive (my mood is not that low and I feel like I can finally live- I feel like I can sort of breath again).\nAs soon. As we got to the car - she changed; she was mean and talking to me like I was the problem and that I did something wrong (I felt suffocated again).\nIt's honestly mood swings and it's too much - it's like I have to walk around egg shells. I never know when she is going go from nice to abusive. It's giving me whiplash. And its no wonder why I would be so confused with my mother when I was a kid; she would be \"nice\" then turn abusive and what made it worse is that she add in love bombing and gaslighting.\nToday when we were in the store she tried to gaslight me about fucking cucumbers saying she gave them back to me when she did not. She knew she couldn't win and dropped it saying oh I don't know wear I put it."

    generator = PostMetadataGenerator()

    for i in range(1):
        print('-'*50)
        metadata_dict = generator.generate_youtube_metadata(content)
        for k,v in metadata_dict.items():
            print(f"{k}: {v}")
