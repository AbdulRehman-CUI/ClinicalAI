import inspect
from google import genai
from google.genai import types

print('google.genai module:', genai.__file__)
print('Client init:', inspect.signature(genai.Client))
print('GenerateContentConfig init:', inspect.signature(types.GenerateContentConfig))
print('models.generate_content sig:', inspect.signature(genai.Client.models.generate_content))
