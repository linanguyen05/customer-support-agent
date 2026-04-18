# agent.py 
from mock_api import mock_order_status
from bedrock_client import BedrockClient
from config import SYSTEM_PROMPT

ORDER_STATUS_TOOL = {
    "toolSpec": {
        "name": "check_order_status",
        "description": "Call this tool ONLY when ALL three fields are provided: full_name, ssn_last4 (exactly 4 digits), dob (YYYY-MM-DD). Never guess any value.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "ssn_last4": {"type": "string"},
                    "dob": {"type": "string"}
                },
                "required": ["full_name", "ssn_last4", "dob"]
            }
        }
    }
}

SYSTEM_PROMPT = SYSTEM_PROMPT.strip() 

class Agent:
    def __init__(self, retriever):
        self.retriever = retriever
        self.bedrock = BedrockClient()
        self.messages = []
        self.max_history = 20
        # Light state for order collection (Level 100 friendly)
        self.pending_order_info = {"full_name": None, "ssn_last4": None, "dob": None}

    def _update_order_info(self, user_input: str):
        """Light parsing to accumulate order fields from user message"""
        lowered = user_input.lower()
        
        # Full name (simple but improved)
        if "name" in lowered or "tên" in lowered or "my name is" in lowered:
            import re
            name_match = re.search(r"(?:tên|name|my name is|full name)[^\w]*([A-Za-zÀ-ỹ\s]+?)(?:,|\.|ssn|dob|birth|$)", user_input, re.IGNORECASE)
            if name_match:
                name_part = name_match.group(1).strip()
                if name_part and not any(c.isdigit() for c in name_part):
                    self.pending_order_info["full_name"] = name_part

        # SSN last 4
        import re
        ssn_match = re.search(r'\b(\d{4})\b', user_input)
        if ssn_match:
            self.pending_order_info["ssn_last4"] = ssn_match.group(1)

        # DOB
        dob_match = re.search(r'(\d{4}-\d{2}-\d{2})', user_input)
        if dob_match:
            self.pending_order_info["dob"] = dob_match.group(1)

        # Reject masked values
        for key in self.pending_order_info:
            if self.pending_order_info[key] and "****" in str(self.pending_order_info[key]):
                self.pending_order_info[key] = None

    def _has_complete_order_info(self):
        return all(self.pending_order_info.values())

    def _build_user_message(self, user_input: str) -> str:
        print(f"[DEBUG] Before update: {self.pending_order_info}")  # THÊM DÒNG NÀY
        self._update_order_info(user_input) # Accumulate fields
        print(f"[DEBUG] After update: {self.pending_order_info}") 

        docs = self.retriever.get_relevant_documents(user_input)
        context_text = "\n\n".join(
            [f"[Page {doc.metadata.get('page')}]: {doc.page_content.strip()}" for doc in docs]
        ) if docs else "(none)"

        order_status = "You have provided order info: " + str(self.pending_order_info) if any(self.pending_order_info.values()) else ""

        return f"""Relevant information from company documents:
{context_text}

{order_status}

User question: {user_input}"""

    def _trim_history(self):
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def _clear_if_orphan_tool_use(self):
        pending = set()
        for msg in self.messages:
            role = msg.get("role")
            for block in msg.get("content", []):
                if role == "assistant" and "toolUse" in block:
                    tool_id = block["toolUse"].get("toolUseId")
                    if tool_id:
                        pending.add(tool_id)
                elif role == "user" and "toolResult" in block:
                    tool_id = block["toolResult"].get("toolUseId")
                    if tool_id in pending:
                        pending.remove(tool_id)
        if pending:
            print("[WARN] Orphan toolUse detected. Clearing conversation state.")
            self.clear_history()
    
    def respond(self, user_input: str):
        self._clear_if_orphan_tool_use()

        # Accumulate order info
        self._update_order_info(user_input)

        current_user_content = self._build_user_message(user_input)

        api_messages = self.messages.copy()
        api_messages.append({
            "role": "user",
            "content": [{"text": current_user_content}]
        })

        response = self.bedrock.converse(
            messages=api_messages,
            tools=[ORDER_STATUS_TOOL],
            system_prompt=SYSTEM_PROMPT
        )

        stop_reason = response.get("stopReason")
        output_msg = response.get("output", {}).get("message", {})
        content_blocks = output_msg.get("content", [])

        if stop_reason == "tool_use":
            tool_messages = api_messages.copy()
            tool_messages.append({"role": "assistant", "content": content_blocks})

            for block in content_blocks:
                if "toolUse" not in block:
                    continue
                tool_use = block["toolUse"]
                tool_id = tool_use["toolUseId"]
                tool_input = tool_use.get("input", {})

                result = mock_order_status(
                    full_name=tool_input.get("full_name", ""),
                    ssn_last4=tool_input.get("ssn_last4", ""),
                    dob=tool_input.get("dob", "")
                )

                tool_messages.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": [{"json": result}]
                        }
                    }]
                })

            final_response = self.bedrock.converse(
                messages=tool_messages,
                tools=[ORDER_STATUS_TOOL],
                system_prompt=SYSTEM_PROMPT
            )

            final_text = final_response.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "Error processing request.")

            # Reset order state sau khi gọi tool thành công
            if result.get("status") != "error":
                self.pending_order_info = {"full_name": None, "ssn_last4": None, "dob": None}

            self.messages = tool_messages + [{"role": "assistant", "content": [{"text": final_text}]}]
            self._trim_history()
            return final_text

        # Normal response
        assistant_text = output_msg.get("content", [{}])[0].get("text", "Error processing request.")

        self.messages = api_messages + [{"role": "assistant", "content": [{"text": assistant_text}]}]
        self._trim_history()
        return assistant_text

    def respond_stream(self, user_input: str):
        """Generator cho streaming responses - chỉ dùng cho câu hỏi knowledge (không order)"""
        # Nếu là order query, fallback sang respond (non-stream)
        order_keywords = ["order", "shipment", "tracking", "delivery status", "where is my package", "check my order"]
        if any(kw in user_input.lower() for kw in order_keywords):
            full_response = self.respond(user_input)
            yield full_response
            return

        # Knowledge question: dùng streaming
        self._clear_if_orphan_tool_use()
        self._update_order_info(user_input)  # vẫn cập nhật phòng trường hợp user cung cấp thông tin lẻ tẻ
        current_user_content = self._build_user_message(user_input)
        api_messages = self.messages.copy()
        api_messages.append({"role": "user", "content": [{"text": current_user_content}]})
        
        # Gọi Bedrock stream (không tool)
        stream_gen = self.bedrock.converse_stream(messages=api_messages, tools=None, system_prompt=SYSTEM_PROMPT)
        full_text = ""
        for chunk in stream_gen:
            full_text += chunk
            yield chunk
        # Lưu lịch sử
        self.messages = api_messages + [{"role": "assistant", "content": [{"text": full_text}]}]
        self._trim_history()

    def clear_history(self):
        print("[DEBUG] clear_history called!")
        self.messages = []
        self.pending_order_info = {"full_name": None, "ssn_last4": None, "dob": None}