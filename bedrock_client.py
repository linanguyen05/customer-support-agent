# # bedrock_client.py
# import boto3
# import json
# from config import REGION, EMBEDDING_MODEL_ID, LLM_MODEL_ID


# class BedrockClient:
#     def __init__(self):
#         self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

#     def get_embedding(self, text: str):
#         body = json.dumps({"inputText": text})
#         response = self.bedrock_runtime.invoke_model(
#             modelId=EMBEDDING_MODEL_ID,
#             contentType="application/json",
#             accept="application/json",
#             body=body
#         )
#         result = json.loads(response["body"].read())
#         return result["embedding"]

#     def converse(self, messages, tools=None, system_prompt=""):
#         request = {
#             "modelId": LLM_MODEL_ID,
#             "messages": messages,
#             "system": [{"text": system_prompt}],
#             "inferenceConfig": {
#                 "temperature": 0.0,
#                 "maxTokens": 1000
#             }
#         }

#         if tools:
#             request["toolConfig"] = {"tools": tools}

#         try:
#             print(f"[DEBUG] Calling Bedrock: tools_enabled={tools is not None}, messages_count={len(messages)}")
#             response = self.bedrock_runtime.converse(**request)

#             response_dict = {
#                 "stopReason": response.get("stopReason"),
#                 "output": {
#                     "message": {
#                         "role": response.get("output", {}).get("message", {}).get("role"),
#                         "content": []
#                     }
#                 }
#             }

#             content_blocks = response.get("output", {}).get("message", {}).get("content", [])
#             for block in content_blocks:
#                 if "text" in block:
#                     response_dict["output"]["message"]["content"].append({
#                         "text": block["text"]
#                     })
#                 elif "toolUse" in block:
#                     tool_use = block["toolUse"]
#                     response_dict["output"]["message"]["content"].append({
#                         "toolUse": {
#                             "toolUseId": tool_use.get("toolUseId"),
#                             "name": tool_use.get("name"),
#                             "input": tool_use.get("input", {})
#                         }
#                     })

#             return response_dict

#         except Exception as e:
#             print(f"[ERROR] Bedrock call failed: {e}")
#             return {
#                 "stopReason": "error",
#                 "output": {
#                     "message": {
#                         "role": "assistant",
#                         "content": [{"text": f"System error: {str(e)}"}]
#                     }
#                 }
#             }

import boto3
import json
from config import REGION, EMBEDDING_MODEL_ID, LLM_MODEL_ID

class BedrockClient:
    def __init__(self):
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

    def get_embedding(self, text: str):
        body = json.dumps({"inputText": text})
        response = self.bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    def converse(self, messages, tools=None, system_prompt=""):
        request = {
            "modelId": LLM_MODEL_ID,
            "messages": messages,
            "system": [{"text": system_prompt}],
            "inferenceConfig": {"temperature": 0.0, "maxTokens": 1000}
        }
        if tools:
            request["toolConfig"] = {"tools": tools}
        try:
            response = self.bedrock_runtime.converse(**request)
            # parse response (giữ nguyên như cũ)
            return self._parse_converse_response(response)
        except Exception as e:
            print(f"[ERROR] Bedrock call failed: {e}")
            return {"stopReason": "error", "output": {"message": {"role": "assistant", "content": [{"text": f"System error: {str(e)}"}]}}}

    def converse_stream(self, messages, tools=None, system_prompt=""):
        """Generator trả về text chunks. Chỉ dùng khi không có tool call."""
        request = {
            "modelId": LLM_MODEL_ID,
            "messages": messages,
            "system": [{"text": system_prompt}],
            "inferenceConfig": {"temperature": 0.0, "maxTokens": 1000}
        }
        if tools:
            request["toolConfig"] = {"tools": tools}
        try:
            response_stream = self.bedrock_runtime.converse_stream(**request)
            for event in response_stream["stream"]:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        yield delta["text"]
                # Bỏ qua các event khác (toolUse, metadata)
        except Exception as e:
            yield f"\n[Error] {str(e)}"

    def _parse_converse_response(self, response):
        # Hàm parse giống như code cũ của bạn
        response_dict = {
            "stopReason": response.get("stopReason"),
            "output": {
                "message": {
                    "role": response.get("output", {}).get("message", {}).get("role"),
                    "content": []
                }
            }
        }
        content_blocks = response.get("output", {}).get("message", {}).get("content", [])
        for block in content_blocks:
            if "text" in block:
                response_dict["output"]["message"]["content"].append({"text": block["text"]})
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                response_dict["output"]["message"]["content"].append({
                    "toolUse": {
                        "toolUseId": tool_use.get("toolUseId"),
                        "name": tool_use.get("name"),
                        "input": tool_use.get("input", {})
                    }
                })
        return response_dict