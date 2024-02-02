import openai
import time
import random
from src.config import OPENAI_KEY, OPENAI_API_VERSION, OPENAI_API_BASE, OPENAI_API_TYPE, COMPLETION_OPENAI_KEY, COMPLETION_OPENAI_API_VERSION, COMPLETION_OPENAI_API_BASE, COMPLETION_OPENAI_API_TYPE
from src.logger import logger

class OpenAIClient:
    def __init__(self):
        openai.api_type = OPENAI_API_TYPE
        openai.api_key = OPENAI_KEY
        openai.api_base = OPENAI_API_BASE
        openai.api_version = OPENAI_API_VERSION
        logger.info("STATUS: OpenAI Object Created Successfully!")

    def create_embedding_docs(self, content):
        openai.api_type = OPENAI_API_TYPE
        openai.api_key = OPENAI_KEY
        openai.api_base = OPENAI_API_BASE
        openai.api_version = OPENAI_API_VERSION

        res = []

        for i in range(len(content)):
            embedding = openai.Embedding.create(input=content[i],engine='text-embedding-ada-002')
            embedding = embedding['data'][0]['embedding']
            res.append(embedding)

            if (len(res) == len(content)):
                return True, res
            
            return False, []

    def create_embedding(self, text, conversation_id):
        openai.api_type = OPENAI_API_TYPE
        openai.api_key = OPENAI_KEY
        openai.api_base = OPENAI_API_BASE
        openai.api_version = OPENAI_API_VERSION

        for delay_secs in (2**x for x in range(0, 4)):
            try:
                logger.info(f"{conversation_id} - Creating Embedding!")
                response = openai.Embedding.create(
                    input=text, engine='text-embedding-ada-002'
                )
                embedding = response["data"][0]["embedding"]
                logger.info(f"{conversation_id} - Embedding created successfully!")
                return embedding
            except Exception as ex:
                logger.error(f'{conversation_id} - Embedding creation failed due to {ex}', exc_info=True)
                random_value = random.randint(0, 1000) / 1000.0
                sleep_dur = delay_secs + random_value
                time.sleep(sleep_dur)
                continue
        return []
    
    def rephrase_query(self, query, pairs, model, conversation_id):
        openai.api_type = COMPLETION_OPENAI_API_TYPE
        openai.api_key = COMPLETION_OPENAI_KEY
        openai.api_base = COMPLETION_OPENAI_API_BASE
        openai.api_version = COMPLETION_OPENAI_API_VERSION

        try:
            system_prompt = '''Given the following conversation and a follow up input, analyze the follow up input and rephrase it to be a standalone question if it is regarding the ongoing conversation or respond with "Not a follow-up question" if it's not.
                                Response format: "REPHRASED QUERY: rephrased query" / "Not a follow-up question"
                                - You will always rephrase queries in English.
                                - Responses will follow the specified format.
                                - You will respond with "Not a follow-up question" if the followup input is not regarding the ongoing conversation.
                                - Carefully provide the rephrased question by not missing any relevant details in the given conversation that are needed to answer the follow up question.
                                - You will never provide answers to the follow up question/input nor you would require additional information to rephrase it.
                                - Do not refer by using terms such as 'previous answer', 'mentioned earlier', 'it', 'that', 'this' etc in the rephrased question, add all the necessary information needed in the rephrased question itself.
                            '''
            message = [{'role': 'system', 'content': system_prompt}]

            for pair in pairs:
                message.append({
                    'role': 'user',
                    'content': f"Old Question: {pair['Q']}"
                })

                try:
                    ans = pair['A']['answer']
                    message.append({
                        'role': 'assistant',
                        'content': f"Old Answer: {ans}"
                    })
                except Exception as ex:
                    print('error in try', ex)
                    message.append({'role': 'assistant','content': f"Old Answer: {pair['A']}"})

            message.append({'role': 'user',
                'content': f'Follow up input: {query}\nResponse: '})

            logger.info(f'{conversation_id} - calling chat completion for rephrased query.')
            rephrased_query = self.chat_completion(message, model, conversation_id)

            if(rephrased_query=='OpenAI Not Responding'):
                return rephrased_query
            
            if('not a follow-up question' in rephrased_query.lower() or 'not a followup question' in rephrased_query.lower()):
                rephrased_query = query
            else:
                try:
                    rephrased_query = rephrased_query.split(":")[1].strip()
                except Exception as ex:
                    rephrased_query = rephrased_query.split(":")[-1].strip()
                    
            final_res = rephrased_query.replace("Rephrased Query","")
            logger.info(f'{conversation_id} - final rephrased query: {final_res}')
            return final_res
        
        except Exception as ex:
            logger.error(f'{conversation_id} - Rephrase query for {model} failed due to {ex}', exc_info=True)
            return query

    def chat_completion_json_format(self, messages, model, conversation_id):
        openai.api_type = COMPLETION_OPENAI_API_TYPE
        openai.api_key = COMPLETION_OPENAI_KEY
        openai.api_base = COMPLETION_OPENAI_API_BASE
        openai.api_version = COMPLETION_OPENAI_API_VERSION

        response = "OpenAI Not Responding"
        for delay_secs in (2**x for x in range(0, 4)):
            try:
                logger.info(f"{conversation_id} - Chat completion for {model} called!")
                response = openai.ChatCompletion.create(
                    engine=model,
                    messages=messages,
                    temperature=0,
                    seed=70,
                    max_tokens=1100,
                    response_format={"type": "json_object"}
                )
                usage = response['usage']
                response=response['choices'][0]['message']['content'].strip()
                logger.info(f"{conversation_id} - Chat completion for {model} successfull!")
                logger.info(f"{conversation_id} - Response: {response}")
                logger.info(f"{conversation_id} - Usage: {usage}")
                return response 
            except Exception as ex:
                logger.error(f'{conversation_id} - Chat completion for {model} failed due to {ex}', exc_info=True)
                random_value = random.randint(0, 1000) / 1000.0
                sleep_dur = delay_secs + random_value
                time.sleep(sleep_dur)
                continue
        return response
    
    def chat_completion(self, messages, model, conversation_id):
        openai.api_type = COMPLETION_OPENAI_API_TYPE
        openai.api_key = COMPLETION_OPENAI_KEY
        openai.api_base = COMPLETION_OPENAI_API_BASE
        openai.api_version = COMPLETION_OPENAI_API_VERSION

        response = "OpenAI Not Responding"
        for delay_secs in (2**x for x in range(0, 4)):
            try:
                logger.info(f"{conversation_id} - Chat completion for {model} called!")
                response = openai.ChatCompletion.create(
                    engine=model,
                    messages=messages,
                    temperature=0,
                    seed=30,
                    max_tokens=100
                )
                usage = response['usage']
                response = response["choices"][0]["message"]["content"].strip()
                logger.info(f"{conversation_id} - Chat completion for {model} successfull!")
                logger.info(f"{conversation_id} - Response: {response}")
                logger.info(f"{conversation_id} - Usage: {usage}")
                return response
            except Exception as ex:
                logger.error(f'{conversation_id} - Chat completion for {model} failed due to {ex}', exc_info=True)
                random_value = random.randint(0, 1000) / 1000.0
                sleep_dur = delay_secs + random_value
                time.sleep(sleep_dur)
                continue
        return response

    def create_prompt(self, query, relevant_content, model, conversation_id):
        try:
            messages = []
            if(model=='gpt-35-turbo'):
                logger.info(f"{conversation_id} - using gpt 3.5")
                SYSTEM_PROMPT = f"""Role: I am an Expert QnA Bot, mandated to provide answers exclusively from the given Context.
Principle: I provide responses that are strictly derived from Context, void of personal knowledge or insights. Only answers present within Context are permissible.
Objective: Utilize information from multiple sections within the given Context to create a single comprehensive response. If a query falls outside of the Context, the response will be: "Not Found"

Context:
------
{relevant_content}
------

Output Format: Format your answer as JSON with two keys: 'pdf_name' and 'answer'.
The 'answer' key should be a markdown string formatted according to the below output format instructions. 

Output Format Instructions:
- Use Markdown rendering elements for visually appealing responses.
- Utilize headings when necessary for organizing information into sections.
- Use compact tables for structured data presentation.
- Bold relevant parts of responses for improved readability.
- Use short lists to present multiple items or options concisely.

Mandatory Rules:
- Handle and respond to greeting queries.
- Prohibition: Strictly refrain from responses to queries which does not have the answer in Context.
- Response Language: Responses must be delivered in the English language with consistency.
- Respond in a chatbot-like manner and provide responses according to the user's perspective, using only the given context.
- Answer throughly and completely to the user query.
- Never mention that you are answering from "Context" in the final response.
- Important: Each key in the JSON Response should be a standalone/independent and must not contain any mentions/details and information to the other keys."""
                
            else:
                logger.info(f"{conversation_id} - using gpt 4")
                SYSTEM_PROMPT = f"""Role: I am an Expert QnA Bot, mandated to provide answers exclusively from the given Context.
Principle: I provide responses that are strictly derived from Context, void of personal knowledge or insights. Only answers present within Context are permissible.
Objective: Utilize information from multiple sections within the given Context to create a single comprehensive response. If a query falls outside of the Context, the response will be: "Not Found"

Context:
------
{relevant_content}
------

Output Format: Format your answer as JSON with two keys: 'pdf_name' and 'answer'.
The 'answer' key should be a markdown string formatted according to the below output format instructions. 

Output Format Instructions:
- Use Markdown rendering elements for visually appealing responses.
- Utilize headings when necessary for organizing information into sections.
- Use compact tables for structured data presentation.
- Bold relevant parts of responses for improved readability.
- Use short lists to present multiple items or options concisely.

Mandatory Rules:
- Handle and respond to greeting queries.
- Prohibition: Strictly refrain from responses to queries which does not have the answer in Context.
- Response Language: Responses must be delivered in the English language with consistency.
- Respond in a chatbot-like manner and provide responses according to the user's perspective, using only the given context.
- Answer throughly and completely to the user query.
- Never mention that you are answering from "Context" in the final response.
- Important: Each key in the JSON Response should be a standalone/independent and must not contain any mentions/details and information to the other keys."""
        
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
            messages.append({"role": "user", "content": f"Query: {query}\nJSON Response: "})

            return messages

        except Exception as ex:
            logger.error(f'{conversation_id} - Prompt creation for {model} failed due to {ex}', exc_info=True)
            return []

