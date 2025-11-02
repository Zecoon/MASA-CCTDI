import json
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class BaseAgent:
    """智能体基类"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')

    def _clean_json_response(self, response: str) -> str:
        """清理LLM返回的JSON响应，移除markdown代码块等格式标记"""
        if not response:
            return response

        # 移除markdown代码块格式
        # 匹配 ```json\n{...}\n``` 或 ```{...}```
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', response.strip())
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)

        # 移除可能的反引号
        cleaned = cleaned.strip('`').strip()

        return cleaned

    def _call_llm(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 800, max_retries: int = 3) -> str:
        """调用大语言模型，支持自动重试"""
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                content = response.choices[0].message.content

                # 记录成功日志
                if attempt > 0:
                    print(f"✅ [{self.agent_name}] LLM调用在第{attempt + 1}次尝试后成功")

                return content

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                print(f"⚠️ [{self.agent_name}] LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {error_type} - {str(e)}")

                # 如果不是最后一次尝试，等待后重试（指数退避）
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1  # 1秒, 2秒, 4秒...
                    print(f"⏳ [{self.agent_name}] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        # 所有重试都失败
        error_msg = f"调用LLM时发生错误（{max_retries}次重试后失败）: {str(last_error)}"
        print(f"❌ [{self.agent_name}] {error_msg}")
        return error_msg

class ScenarioDirectorAgent(BaseAgent):
    """情景化导演Agent - 负责整个系统运作和维度推进"""
    
    def __init__(self):
        super().__init__("ScenarioDirector")
        self.cctdi_dimensions = {
            1: {"name": "寻找真理", "questions": list(range(1, 11)), "description": "评估个体寻求真理和准确信息的倾向"},
            2: {"name": "开放思想", "questions": list(range(11, 21)), "description": "评估个体对不同观点和想法的开放程度"},
            3: {"name": "分析能力", "questions": list(range(21, 31)), "description": "评估个体分析和评估信息的能力"},
            4: {"name": "系统化能力", "questions": list(range(31, 41)), "description": "评估个体系统性思考和解决问题的能力"},
            5: {"name": "批判性思维自信", "questions": list(range(41, 51)), "description": "评估个体对自己批判性思维能力的信心"},
            6: {"name": "求知欲", "questions": list(range(51, 61)), "description": "评估个体对学习和探索新知识的渴望"},
            7: {"name": "认知成熟度", "questions": list(range(61, 71)), "description": "评估个体在复杂情况下做出成熟判断的能力"}
        }
        self.current_dimension = 1
        self.assessment_state = {
            "current_dimension": 1,
            "dimension_progress": {},
            "total_interactions": 0,
            "start_time": datetime.now().isoformat()
        }
        
    def start_assessment(self) -> Dict:
        """开始整个评估流程"""
        self.current_dimension = 1
        self.assessment_state = {
            "current_dimension": 1,
            "dimension_progress": {},
            "total_interactions": 0,
            "start_time": datetime.now().isoformat()
        }
        
        return {
            "status": "started",
            "message": "CCTDI批判性思维评估开始！我们将依次评估7个维度的能力。",
            "current_dimension": self.current_dimension,
            "dimension_info": self._get_current_dimension_info()
        }
    
    def _get_current_dimension_info(self) -> Dict:
        """获取当前维度信息"""
        dim_info = self.cctdi_dimensions[self.current_dimension]
        return {
            "dimension_id": self.current_dimension,
            "dimension_name": dim_info["name"],
            "questions": dim_info["questions"],
            "description": dim_info["description"]
        }
    
    def generate_dimension_guidance(self) -> Dict:
        """生成当前维度的指导性解读和情景化例子"""
        dim_info = self.cctdi_dimensions[self.current_dimension]
        
        system_prompt = f"""
        你是CCTDI批判性思维评估的专家。请为"{dim_info['name']}"维度生成：
        
        1. 深入的能力解读（这个维度具体评估什么能力）
        2. 3个简单的情景化例子（展示这个维度在日常生活中的体现）
        3. 评估重点（在交互中应该关注用户的哪些表现）
        
        维度描述：{dim_info['description']}
        相关题目编号：{dim_info['questions']}
        
        请用中文回答，内容要实用且易于理解。
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        guidance = self._call_llm(messages, temperature=0.3)
        
        return {
            "dimension_id": self.current_dimension,
            "dimension_name": dim_info["name"],
            "guidance": guidance,
            "questions_range": dim_info["questions"],
            "timestamp": datetime.now().isoformat()
        }
    
    def advance_to_next_dimension(self, current_score: int) -> Dict:
        """推进到下一个维度"""
        # 记录当前维度的完成情况
        self.assessment_state["dimension_progress"][self.current_dimension] = {
            "score": current_score,
            "completed_at": datetime.now().isoformat()
        }
        
        # 检查是否还有下一个维度
        if self.current_dimension < 7:
            self.current_dimension += 1
            return {
                "status": "advanced",
                "message": f"维度 {self.current_dimension-1} 评估完成，开始维度 {self.current_dimension}",
                "current_dimension": self.current_dimension,
                "dimension_info": self._get_current_dimension_info(),
                "previous_score": current_score
            }
        else:
            return {
                "status": "completed",
                "message": "所有维度评估完成！",
                "final_results": self.assessment_state["dimension_progress"]
            }
    
    def get_assessment_status(self) -> Dict:
        """获取评估状态"""
        return {
            "current_dimension": self.current_dimension,
            "completed_dimensions": len(self.assessment_state["dimension_progress"]),
            "total_dimensions": 7,
            "progress": self.assessment_state
        }

class AdaptiveNavigatorAgent(BaseAgent):
    """自适应导航Agent - 负责与用户交互提问"""
    
    def __init__(self):
        super().__init__("AdaptiveNavigator")
        self.interaction_modes = ["鼓励", "正常", "追问"]
        self.current_mode = "正常"
        self.interaction_history = []
        
    def set_dimension_context(self, dimension_info: Dict, guidance: Dict):
        """设置当前维度的上下文信息"""
        self.current_dimension = dimension_info
        self.dimension_guidance = guidance
        
    def select_interaction_mode(self, user_responses: List[Dict], interaction_count: int) -> str:
        """选择交互模式：鼓励、正常、追问"""
        if interaction_count == 0:
            return "正常"  # 首次交互使用正常模式
        
        # 分析用户最近的回应
        if len(user_responses) > 0:
            last_response = user_responses[-1].get("content", "")
            
            # 如果回应很短或者消极，使用鼓励模式
            if len(last_response) < 20 or any(word in last_response for word in ["不知道", "不确定", "不会", "难"]):
                return "鼓励"
            
            # 如果回应很详细，使用追问模式深入挖掘
            elif len(last_response) > 100:
                return "追问"
            
            # 其他情况使用正常模式
            else:
                return "正常"
        
        return "正常"
    
    def generate_question(self, user_responses: List[Dict], interaction_count: int) -> Dict:
        """生成针对当前维度的问题"""
        self.current_mode = self.select_interaction_mode(user_responses, interaction_count)
        
        # 构建上下文
        context = f"""
        当前评估维度：{self.current_dimension['dimension_name']}
        维度描述：{self.current_dimension['description']}
        
        维度指导信息：
        {self.dimension_guidance.get('guidance', '')}
        
        交互模式：{self.current_mode}
        交互轮次：{interaction_count + 1}
        """
        
        # 根据交互轮次和模式生成问题
        if interaction_count == 0:
            # 首次交互 - 开场问题
            system_prompt = f"""
            {context}
            
            请生成一个开场问题来评估用户在"{self.current_dimension['dimension_name']}"维度的能力。
            
            要求：
            1. 问题要自然、不刻板
            2. 能够引出用户在该维度的真实表现
            3. 可以是情景化的问题或者开放性讨论
            4. 避免直接问量表题目
            
            只返回问题内容，不要其他解释。
            """
        else:
            # 后续交互 - 根据模式和历史回应生成
            recent_responses = user_responses[-2:] if len(user_responses) >= 2 else user_responses
            responses_text = "\n".join([f"用户: {resp.get('content', '')}" for resp in recent_responses])
            
            mode_instructions = {
                "鼓励": "用鼓励和支持的语气，帮助用户更好地表达想法，可以提供一些引导或例子",
                "正常": "用自然的对话方式继续探索用户在该维度的表现",
                "追问": "深入挖掘用户的思考过程，要求更详细的解释或具体例子"
            }
            
            system_prompt = f"""
            {context}
            
            用户最近的回应：
            {responses_text}
            
            交互模式指导：{mode_instructions[self.current_mode]}
            
            请生成下一个问题来继续评估用户在"{self.current_dimension['dimension_name']}"维度的能力。
            
            要求：
            1. 基于用户之前的回应进行针对性提问
            2. 符合当前的交互模式
            3. 继续深入了解用户在该维度的表现
            4. 保持对话的自然流畅
            
            只返回问题内容，不要其他解释。
            """
        
        messages = [{"role": "system", "content": system_prompt}]
        question = self._call_llm(messages, temperature=0.6)
        
        interaction_data = {
            "interaction_count": interaction_count,
            "mode": self.current_mode,
            "question": question,
            "dimension": self.current_dimension['dimension_name'],
            "timestamp": datetime.now().isoformat()
        }
        
        self.interaction_history.append(interaction_data)
        return interaction_data
    
    def get_interaction_summary(self) -> Dict:
        """获取交互摘要"""
        return {
            "total_interactions": len(self.interaction_history),
            "modes_used": [item["mode"] for item in self.interaction_history],
            "current_dimension": self.current_dimension['dimension_name'] if hasattr(self, 'current_dimension') else None
        }

class DiagnosticAgent(BaseAgent):
    """诊断Agent - 判断信息是否足够支持评分"""
    
    def __init__(self):
        super().__init__("DiagnosticAgent")
        
    def analyze_interaction_sufficiency(self, 
                                      dimension_info: Dict,
                                      guidance_info: Dict, 
                                      interactions: List[Dict],
                                      user_responses: List[Dict]) -> Dict:
        """分析交互是否足够支持评分"""

        # 硬性限制：达到5轮必须评分
        if len(interactions) >= 5:
            return {
                "sufficient": True,
                "reason": "已达到最大交互轮次(5轮)，必须进行评分",
                "recommendation": "score",
                "confidence": 1.0
            }

        # 基本检查：至少3轮交互
        if len(interactions) < 3:
            return {
                "sufficient": False,
                "reason": "交互轮次不足，需要至少3轮交互",
                "recommendation": "continue",
                "confidence": 0.9
            }
        
        # 构建分析上下文
        interaction_summary = "\n".join([
            f"第{i+1}轮 - 模式:{interaction['mode']}\n问题: {interaction['question']}\n用户回应: {user_responses[i].get('content', '') if i < len(user_responses) else '无回应'}\n"
            for i, interaction in enumerate(interactions)
        ])
        
        system_prompt = f"""
        你是CCTDI批判性思维评估的诊断专家。请分析当前的交互是否足够支持对用户在"{dimension_info['dimension_name']}"维度的能力进行准确评分。
        
        维度信息：
        - 维度名称：{dimension_info['dimension_name']}
        - 维度描述：{dimension_info['description']}
        
        维度指导信息：
        {guidance_info.get('guidance', '')}
        
        交互历史：
        {interaction_summary}
        
        请分析以下方面：
        1. 用户回应的质量和深度
        2. 是否充分展现了该维度相关的思维特征
        3. 信息是否足够支持准确评分
        4. 是否需要进一步交互来获取更多信息

        请以JSON格式返回分析结果：
        {{
            "sufficient": true/false,
            "reason": "分析原因",
            "recommendation": "continue/score",
            "confidence": 0.0-1.0,
            "key_insights": ["关键洞察1", "关键洞察2", ...],
            "missing_aspects": ["缺失方面1", "缺失方面2", ...]
        }}

        **重要**：请直接返回纯JSON对象，不要使用markdown代码块（```json）包裹，不要添加任何其他文字说明。
        """
        
        messages = [{"role": "system", "content": system_prompt}]

        # 尝试最多2次获取有效的JSON响应
        for attempt in range(2):
            analysis_result = self._call_llm(messages, temperature=0.3, max_retries=2)

            # 清理响应中的markdown格式
            cleaned_result = self._clean_json_response(analysis_result)

            try:
                # 尝试解析JSON结果
                result = json.loads(cleaned_result)
                result["timestamp"] = datetime.now().isoformat()
                result["analyzed_interactions"] = len(interactions)

                # 验证必需字段
                required_fields = ["sufficient", "reason", "recommendation", "confidence"]
                if all(field in result for field in required_fields):
                    if attempt > 0:
                        print(f"✅ [DiagnosticAgent] JSON解析在第{attempt + 1}次尝试后成功")
                    return result
                else:
                    print(f"⚠️ [DiagnosticAgent] JSON缺少必需字段，尝试重新生成 ({attempt + 1}/2)")

            except json.JSONDecodeError as e:
                print(f"⚠️ [DiagnosticAgent] JSON解析失败 ({attempt + 1}/2): {str(e)}")
                if attempt == 0:
                    print(f"📝 原始响应: {analysis_result[:200]}...")

        # 所有尝试都失败，返回默认结果
        print(f"❌ [DiagnosticAgent] 使用默认判断逻辑")
        return {
            "sufficient": len(interactions) >= 5,  # 超过5轮认为足够
            "reason": "JSON解析失败，使用默认判断逻辑",
            "recommendation": "score" if len(interactions) >= 5 else "continue",
            "confidence": 0.5,
            "key_insights": [],
            "missing_aspects": [],
            "timestamp": datetime.now().isoformat(),
            "analyzed_interactions": len(interactions),
            "raw_analysis": analysis_result
        }

class ScoringAgent(BaseAgent):
    """评分Agent - 对用户当前维度能力进行评分"""
    
    def __init__(self):
        super().__init__("ScoringAgent")
        
    def score_dimension(self,
                       dimension_info: Dict,
                       guidance_info: Dict,
                       interactions: List[Dict],
                       user_responses: List[Dict],
                       diagnostic_analysis: Dict) -> Dict:
        """对用户在当前维度的能力进行评分（10-60分，平均35分）"""
        
        # 构建完整的交互记录
        full_interaction = "\n".join([
            f"=== 第{i+1}轮交互 ===\n"
            f"提问模式: {interactions[i]['mode']}\n"
            f"问题: {interactions[i]['question']}\n"
            f"用户回应: {user_responses[i].get('content', '无回应') if i < len(user_responses) else '无回应'}\n"
            for i in range(len(interactions))
        ])
        
        system_prompt = f"""
        你是CCTDI批判性思维评估的权威评分专家。请基于用户的交互表现，对其在"{dimension_info['dimension_name']}"维度的能力进行准确评分。
        
        === 维度信息 ===
        维度名称：{dimension_info['dimension_name']}
        维度描述：{dimension_info['description']}
        相关题目：{dimension_info['questions']}
        
        === 维度指导 ===
        {guidance_info.get('guidance', '')}
        
        === 诊断分析 ===
        关键洞察：{diagnostic_analysis.get('key_insights', [])}
        分析置信度：{diagnostic_analysis.get('confidence', 0)}
        
        === 完整交互记录 ===
        {full_interaction}
        """

        # 添加维度特定的评分指导
        dimension_specific_guidance = ""
        if dimension_info['dimension_id'] == 3:  # 分析能力
            dimension_specific_guidance = """

        ⚠️ 维度3（分析能力）特别说明：
        - 本维度的基准分应为47分（真实数据均值），而非通用的43分
        - 重点评估：逻辑推理的完整性、论证的严密性、分析的深度
        - 加分项：
          • 识别逻辑谬误（如以偏概全、虚假因果）：+3分
          • 从多个角度分析问题：+3分
          • 构建完整的因果分析链：+3分
          • 提出有力的替代假设或反例：+2分
        - 注意：不要因为表达简洁而扣分，关注思维质量而非文字数量
        - 如果用户展现了系统性的分析方法，应给予45分以上
        - 评分参考：基础表现给42-48分，优秀表现给49-55分
        """
        elif dimension_info['dimension_id'] == 5:  # 批判性思维自信
            dimension_specific_guidance = """

        ⚠️ 维度5（批判性思维自信）特别说明：
        - 本维度的基准分应为45分（真实数据均值），而非通用的43分
        - 评估重点：对自己判断能力的信心，而非对具体观点的确定性
        - 重要提醒：不要被"我觉得""可能""也许"等谦虚用语误导 - 这不代表缺乏自信
        - 关注用户是否：
          • 坚持自己的推理过程
          • 愿意为自己的判断辩护
          • 相信自己的分析能力
          • 即使面对挑战也维持理性判断
        - 加分项：
          • 面对权威观点仍坚持理性判断：+3分
          • 清楚表达自己的推理过程和信心来源：+3分
          • 对自己识别谬误、分析问题的能力有信心：+3分
          • 能理性评估自己判断的可靠性：+2分
        - 承认不确定性但不否定自己能力的用户，应给予42分以上
        - 如果用户在面对挑战时依然坚持理性判断，应给予48分以上
        """

        system_prompt += dimension_specific_guidance
        system_prompt += """

        === 详细评分标准 (10-60分，必须精确到个位数) ===

        **10-20分 - 极差**
        • 10-14分：完全缺乏该维度能力，几乎无相关表现
        • 15-17分：偶尔显示极其有限的相关表现，质量很低
        • 18-20分：有萌芽意识但几乎不稳定，表现极弱

        **21-30分 - 较差**
        • 21-24分：能力明显不足，很少表现出相关思维
        • 25-27分：偶有相关表现但质量低，不够稳定
        • 28-30分：能力较差但开始有基本意识，仍需大幅提升

        **31-40分 - 略低于平均到接近平均 (平均值以下区间)**
        • 31-33分：明显低于平均，表现不够稳定，深度不足
        • 34-36分：略低于平均，有基本表现但仍需提升
        • 37-39分：接近平均，表现尚可但略有不足
        • 40分：接近平均水平，表现基本合格

        **41-50分 - 平均到良好 (新的基准区间，43分为标准平均值)**
        • 41-43分：平均水平，稳定的批判性思维表现，符合常模
        • 44-46分：略高于平均，表现良好且较稳定
        • 47-49分：明显高于平均，表现出色且有深度
        • 50分：良好水平，展现出较强的批判性思维能力

        **51-60分 - 优秀**
        • 51-53分：优秀水平，持续表现高质量思维，很少失误
        • 54-56分：优秀偏上，表现卓越且有洞察力，深度广度兼具
        • 57-59分：接近满分，表现极其出色，几乎无可挑剔
        • 60分：满分，该维度能力顶尖，表现完美

        **关键校准提示（必须严格遵守）：**
        1. 评分标准以43分为平均值基准，这是CCTDI常模的实际均值
        2. 虚拟用户的回答已经相当真实，仅需微调1-2分即可
        3. 在初步判断基础上，实际给分应向下调整1-2分（而非8-10分）
        4. 目标：让大部分用户得分落在38-48分区间，这是真实分布
        5. 38-48分是最常见分数段，要勇于使用这个区间
        6. 50+分虽然较少但对真正优秀的表现应该给予
        7. 相信你的第一判断，不要过度向下调整
        8. 普通正常的表现应该给38-45分，而不是32-38分

        **评分要求 (必须遵守):**
        1. 必须精确到个位数，根据具体表现给出精确分数
        2. 仔细区分相邻分数的细微差别
        3. 不要过度依赖区间中点，要基于实际表现细化评分
        4. 同一等级内的不同分数代表不同程度

        请综合分析用户的回应质量、思维深度、维度相关表现等，给出公正准确且严格的评分。

        请以JSON格式返回评分结果：
        {{
            "score": 分数(10-60),
            "level": "评级(极差/较差/一般/良好/优秀)",
            "reasoning": "详细评分理由",
            "evidence": ["支持评分的具体证据1", "证据2", ...],
            "strengths": ["用户在该维度的优势表现"],
            "weaknesses": ["用户在该维度的不足之处"],
            "confidence": 评分置信度(0.0-1.0)
        }}

        **重要**：请直接返回纯JSON对象，不要使用markdown代码块（```json）包裹，不要添加任何其他文字说明。
        """
        
        messages = [{"role": "system", "content": system_prompt}]

        # 尝试最多2次获取有效的JSON响应
        for attempt in range(2):
            scoring_result = self._call_llm(messages, temperature=0.4, max_tokens=1000, max_retries=2)

            # 清理响应中的markdown格式
            cleaned_result = self._clean_json_response(scoring_result)

            try:
                # 尝试解析JSON结果
                result = json.loads(cleaned_result)

                # 验证必需字段
                required_fields = ["score", "level", "reasoning", "confidence"]
                if not all(field in result for field in required_fields):
                    print(f"⚠️ [ScoringAgent] JSON缺少必需字段，尝试重新生成 ({attempt + 1}/2)")
                    continue

                # 确保分数在有效范围内
                score = result.get("score", 35)
                if score < 10:
                    score = 10
                elif score > 60:
                    score = 60
                result["score"] = score

                # 添加元数据
                result.update({
                    "dimension": dimension_info['dimension_name'],
                    "dimension_id": dimension_info['dimension_id'],
                    "interactions_analyzed": len(interactions),
                    "timestamp": datetime.now().isoformat(),
                    "scorer": "ScoringAgent"
                })

                if attempt > 0:
                    print(f"✅ [ScoringAgent] JSON解析在第{attempt + 1}次尝试后成功")

                return result

            except json.JSONDecodeError as e:
                print(f"⚠️ [ScoringAgent] JSON解析失败 ({attempt + 1}/2): {str(e)}")
                if attempt == 0:
                    print(f"📝 原始响应: {scoring_result[:200]}...")

        # 所有尝试都失败，返回备用评分
        print(f"❌ [ScoringAgent] 使用默认评分机制")
        return {
            "score": 43,  # 默认平均分（已更新为新基准）
            "level": "一般",
            "reasoning": f"JSON解析失败，基于交互轮次({len(interactions)})给出默认评分",
            "evidence": ["交互记录完整", "用户有参与回应"],
            "strengths": ["参与了完整的评估过程"],
            "weaknesses": ["回应质量需要改善"],
            "confidence": 0.3,
            "dimension": dimension_info['dimension_name'],
            "dimension_id": dimension_info['dimension_id'],
            "interactions_analyzed": len(interactions),
            "timestamp": datetime.now().isoformat(),
            "scorer": "ScoringAgent",
            "raw_result": scoring_result
        }

# 测试函数
if __name__ == "__main__":
    print("测试新的CCTDI四智能体系统...")
    
    try:
        # 创建智能体
        director = ScenarioDirectorAgent()
        navigator = AdaptiveNavigatorAgent()
        diagnostic = DiagnosticAgent()
        scorer = ScoringAgent()
        
        print("✅ 所有智能体创建成功！")
        print(f"- 情景化导演Agent: {director.agent_name}")
        print(f"- 自适应导航Agent: {navigator.agent_name}")
        print(f"- 诊断Agent: {diagnostic.agent_name}")
        print(f"- 评分Agent: {scorer.agent_name}")
        
        # 测试基本功能
        assessment_start = director.start_assessment()
        print(f"\n📋 评估开始: {assessment_start['message']}")
        
        guidance = director.generate_dimension_guidance()
        print(f"📖 维度指导已生成: {guidance['dimension_name']}")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
