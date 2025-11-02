import json
import os
import csv
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from cctdi_agents import ScenarioDirectorAgent, AdaptiveNavigatorAgent, DiagnosticAgent, ScoringAgent

# 全局文件锁 - 用于保护 user_scores.csv 的并发写入
_USER_SCORES_LOCK = threading.Lock()

class ConversationCSVManager:
    """对话CSV管理器 - 负责保存对话到CSV文件"""

    def __init__(self, session_id: str):
        """初始化CSV管理器"""
        self.session_id = session_id
        self.csv_dir = "data/conversations"
        self.csv_file = os.path.join(self.csv_dir, f"{session_id}_对话.csv")

        # CSV列名
        self.fieldnames = [
            "会话ID", "维度编号", "维度名称", "对话轮次",
            "时间戳", "角色", "交互模式", "内容", "状态"
        ]

        # 创建目录
        os.makedirs(self.csv_dir, exist_ok=True)

        # 初始化CSV文件（写入表头）
        self._initialize_csv()

    def _initialize_csv(self):
        """初始化CSV文件，写入表头"""
        try:
            with open(self.csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
            print(f"📄 CSV对话文件已创建: {self.csv_file}")
        except Exception as e:
            print(f"⚠️ 创建CSV文件时出错: {e}")

    def _clean_content(self, content: str) -> str:
        """清理内容中的换行符和特殊字符"""
        if not content:
            return ""
        # 将换行符替换为空格
        cleaned = content.replace('\n', ' ').replace('\r', ' ')
        # 移除多余空格
        cleaned = ' '.join(cleaned.split())
        return cleaned

    def save_question(self, dimension_id: int, dimension_name: str,
                     round_num: int, question: str, mode: str, status: str = "进行中"):
        """保存系统问题"""
        self._append_row({
            "会话ID": self.session_id,
            "维度编号": dimension_id,
            "维度名称": dimension_name,
            "对话轮次": round_num,
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "系统",
            "交互模式": mode,
            "内容": self._clean_content(question),
            "状态": status
        })

    def save_user_response(self, dimension_id: int, dimension_name: str,
                          round_num: int, response: str, mode: str, status: str = "进行中"):
        """保存用户回答"""
        self._append_row({
            "会话ID": self.session_id,
            "维度编号": dimension_id,
            "维度名称": dimension_name,
            "对话轮次": round_num,
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "用户",
            "交互模式": mode,
            "内容": self._clean_content(response),
            "状态": status
        })

    def save_dimension_score(self, dimension_id: int, dimension_name: str,
                            score: int, level: str, reasoning: str):
        """保存维度评分结果"""
        score_content = f"【评分】得分:{score}分 | 评级:{level} | 理由:{self._clean_content(reasoning)}"
        self._append_row({
            "会话ID": self.session_id,
            "维度编号": dimension_id,
            "维度名称": dimension_name,
            "对话轮次": "-",
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "系统",
            "交互模式": "评分",
            "内容": score_content,
            "状态": "已完成"
        })

    def save_final_summary(self, total_score: int, average_score: float,
                          overall_level: str, dimension_count: int):
        """保存最终总结"""
        summary_content = f"【总结】总分:{total_score}/420分 | 平均分:{average_score}分 | 总体评级:{overall_level} | 完成维度:{dimension_count}/7"
        self._append_row({
            "会话ID": self.session_id,
            "维度编号": "-",
            "维度名称": "评估完成",
            "对话轮次": "-",
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "系统",
            "交互模式": "总结",
            "内容": summary_content,
            "状态": "已完成"
        })

    def _append_row(self, row_data: Dict):
        """追加一行数据到CSV文件"""
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(row_data)
        except Exception as e:
            print(f"⚠️ 保存CSV数据时出错: {e}")

class CCTDIAssessmentSystem:
    """CCTDI评估系统主控制器"""
    
    def __init__(self, user_id: str = None, user_name: str = None):
        """初始化四个智能体和系统状态

        Args:
            user_id: 用户编号 (可选)
            user_name: 用户姓名 (可选)
        """
        self.director = ScenarioDirectorAgent()
        self.navigator = AdaptiveNavigatorAgent()
        self.diagnostic = DiagnosticAgent()
        self.scorer = ScoringAgent()

        # 用户信息
        self.user_id = user_id
        self.user_name = user_name

        # 生成session_id（如果有用户信息，使用"编号+姓名"，否则使用时间戳）
        session_id = self._generate_session_id()

        # 系统状态
        self.system_state = {
            "status": "initialized",  # initialized, running, completed
            "current_dimension": None,
            "interactions": [],
            "user_responses": [],
            "dimension_scores": {},
            "session_id": session_id
        }

        # 初始化CSV对话管理器
        self.csv_manager = ConversationCSVManager(session_id)

        # 当前维度的工作状态
        self.current_work_state = {
            "dimension_info": None,
            "guidance": None,
            "interaction_count": 0,
            "diagnostic_results": [],
            "ready_for_scoring": False
        }
        
    def _generate_session_id(self) -> str:
        """生成会话ID

        如果有用户信息(user_id和user_name)，返回"编号+姓名"
        否则返回时间戳格式
        """
        if self.user_id and self.user_name:
            return f"{self.user_id}{self.user_name}"
        else:
            return f"cctdi_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def start_assessment(self) -> Dict:
        """开始评估流程"""
        print("🎯 启动CCTDI批判性思维评估系统...")
        
        # 1. 导演Agent启动评估
        director_result = self.director.start_assessment()
        self.system_state["status"] = "running"
        self.system_state["current_dimension"] = director_result["current_dimension"]
        
        # 2. 生成当前维度的指导信息
        guidance = self.director.generate_dimension_guidance()
        self.current_work_state["dimension_info"] = director_result["dimension_info"]
        self.current_work_state["guidance"] = guidance
        
        # 3. 设置导航Agent的维度上下文
        self.navigator.set_dimension_context(
            director_result["dimension_info"], 
            guidance
        )
        
        # 4. 生成首个问题
        first_question = self.navigator.generate_question([], 0)
        self.system_state["interactions"].append(first_question)
        self.current_work_state["interaction_count"] = 1

        # 5. 保存首个问题到CSV
        self.csv_manager.save_question(
            dimension_id=director_result["dimension_info"]["dimension_id"],
            dimension_name=guidance["dimension_name"],
            round_num=1,
            question=first_question["question"],
            mode=first_question["mode"],
            status="进行中"
        )

        return {
            "status": "started",
            "session_id": self.system_state["session_id"],
            "message": "欢迎参加CCTDI批判性思维评估！",
            "current_dimension": guidance["dimension_name"],
            "guidance": guidance["guidance"],
            "first_question": first_question["question"],
            "dimension_progress": "1/7"
        }
    
    def process_user_response(self, user_input: str) -> Dict:
        """处理用户回应"""
        if self.system_state["status"] != "running":
            return {"error": "评估未开始或已结束"}
        
        # 记录用户回应
        user_response = {
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "interaction_id": len(self.system_state["user_responses"])
        }
        self.system_state["user_responses"].append(user_response)

        # 保存用户回答到CSV
        current_round = len(self.system_state["user_responses"])
        last_interaction = self.system_state["interactions"][-1]
        self.csv_manager.save_user_response(
            dimension_id=self.current_work_state["dimension_info"]["dimension_id"],
            dimension_name=self.current_work_state["dimension_info"]["dimension_name"],
            round_num=current_round,
            response=user_input,
            mode=last_interaction["mode"],
            status="进行中"
        )

        print(f"📝 用户回应已记录 (第{len(self.system_state['user_responses'])}轮)")

        # 检查是否需要诊断（3轮后开始,5轮时强制评分）
        if len(self.system_state["user_responses"]) >= 3:
            diagnostic_result = self.diagnostic.analyze_interaction_sufficiency(
                self.current_work_state["dimension_info"],
                self.current_work_state["guidance"],
                self.system_state["interactions"],
                self.system_state["user_responses"]
            )
            
            self.current_work_state["diagnostic_results"].append(diagnostic_result)
            print(f"🔍 诊断结果: {diagnostic_result['recommendation']} (置信度: {diagnostic_result['confidence']:.2f})")
            
            # 如果诊断认为信息足够，进行评分
            if diagnostic_result["sufficient"] and diagnostic_result["recommendation"] == "score":
                return self._score_current_dimension(diagnostic_result)
        
        # 如果还需要继续交互，生成下一个问题
        next_question = self.navigator.generate_question(
            self.system_state["user_responses"],
            self.current_work_state["interaction_count"]
        )

        self.system_state["interactions"].append(next_question)
        self.current_work_state["interaction_count"] += 1

        # 保存下一个问题到CSV
        self.csv_manager.save_question(
            dimension_id=self.current_work_state["dimension_info"]["dimension_id"],
            dimension_name=self.current_work_state["dimension_info"]["dimension_name"],
            round_num=self.current_work_state["interaction_count"],
            question=next_question["question"],
            mode=next_question["mode"],
            status="进行中"
        )

        return {
            "status": "continue",
            "next_question": next_question["question"],
            "interaction_mode": next_question["mode"],
            "interaction_count": self.current_work_state["interaction_count"],
            "dimension": self.current_work_state["dimension_info"]["dimension_name"]
        }
    
    def _score_current_dimension(self, diagnostic_result: Dict) -> Dict:
        """对当前维度进行评分"""
        print(f"📊 开始对维度 '{self.current_work_state['dimension_info']['dimension_name']}' 进行评分...")
        
        # 调用评分Agent
        scoring_result = self.scorer.score_dimension(
            self.current_work_state["dimension_info"],
            self.current_work_state["guidance"],
            self.system_state["interactions"],
            self.system_state["user_responses"],
            diagnostic_result
        )
        
        # 保存维度评分
        dimension_id = self.current_work_state["dimension_info"]["dimension_id"]
        self.system_state["dimension_scores"][dimension_id] = scoring_result

        # 保存评分结果到CSV
        self.csv_manager.save_dimension_score(
            dimension_id=dimension_id,
            dimension_name=self.current_work_state["dimension_info"]["dimension_name"],
            score=scoring_result["score"],
            level=scoring_result["level"],
            reasoning=scoring_result.get("reasoning", "")
        )

        print(f"✅ 维度评分完成: {scoring_result['score']}分 ({scoring_result['level']})")
        
        # 让导演Agent推进到下一个维度
        advance_result = self.director.advance_to_next_dimension(scoring_result["score"])
        
        if advance_result["status"] == "completed":
            # 所有维度完成
            return self._complete_assessment(scoring_result)
        else:
            # 推进到下一个维度
            return self._advance_to_next_dimension(advance_result, scoring_result)
    
    def _advance_to_next_dimension(self, advance_result: Dict, previous_score_result: Dict) -> Dict:
        """推进到下一个维度"""
        print(f"➡️ 推进到维度 {advance_result['current_dimension']}: {advance_result['dimension_info']['dimension_name']}")
        
        # 更新系统状态
        self.system_state["current_dimension"] = advance_result["current_dimension"]
        
        # 重置当前工作状态
        self.current_work_state = {
            "dimension_info": advance_result["dimension_info"],
            "guidance": None,
            "interaction_count": 0,
            "diagnostic_results": [],
            "ready_for_scoring": False
        }
        
        # 清空交互历史（为新维度准备）
        self.system_state["interactions"] = []
        self.system_state["user_responses"] = []
        
        # 生成新维度的指导信息
        guidance = self.director.generate_dimension_guidance()
        self.current_work_state["guidance"] = guidance
        
        # 设置导航Agent的新维度上下文
        self.navigator.set_dimension_context(advance_result["dimension_info"], guidance)
        
        # 生成新维度的首个问题
        first_question = self.navigator.generate_question([], 0)
        self.system_state["interactions"].append(first_question)
        self.current_work_state["interaction_count"] = 1

        # 保存新维度的首个问题到CSV
        self.csv_manager.save_question(
            dimension_id=advance_result["dimension_info"]["dimension_id"],
            dimension_name=guidance["dimension_name"],
            round_num=1,
            question=first_question["question"],
            mode=first_question["mode"],
            status="进行中"
        )

        return {
            "status": "dimension_completed",
            "previous_dimension_result": {
                "name": previous_score_result["dimension"],
                "score": previous_score_result["score"],
                "level": previous_score_result["level"]
            },
            "new_dimension": {
                "name": guidance["dimension_name"],
                "guidance": guidance["guidance"],
                "first_question": first_question["question"]
            },
            "progress": f"{advance_result['current_dimension']}/7"
        }
    
    def _complete_assessment(self, final_score_result: Dict) -> Dict:
        """完成整个评估"""
        print("🎉 所有维度评估完成！")
        
        self.system_state["status"] = "completed"
        
        # 计算总分和总体评级
        total_score = sum(result["score"] for result in self.system_state["dimension_scores"].values())
        average_score = total_score / 7
        
        # 确定总体评级
        if total_score >= 350:
            overall_level = "优秀"
        elif total_score >= 280:
            overall_level = "良好"
        elif total_score >= 210:
            overall_level = "一般"
        elif total_score >= 140:
            overall_level = "较差"
        else:
            overall_level = "极差"
        
        # 生成最终报告
        final_report = {
            "status": "completed",
            "session_id": self.system_state["session_id"],
            "completion_time": datetime.now().isoformat(),
            "total_score": total_score,
            "average_score": round(average_score, 1),
            "overall_level": overall_level,
            "dimension_scores": self.system_state["dimension_scores"],
            "final_dimension_result": {
                "name": final_score_result["dimension"],
                "score": final_score_result["score"],
                "level": final_score_result["level"]
            }
        }
        
        # 保存评估报告
        self._save_assessment_report(final_report)

        # 保存最终总结到CSV
        self.csv_manager.save_final_summary(
            total_score=total_score,
            average_score=average_score,
            overall_level=overall_level,
            dimension_count=7
        )

        # 保存用户评分汇总CSV
        self._save_user_score_summary(total_score)

        return final_report
    
    def _save_assessment_report(self, report: Dict):
        """保存评估报告"""
        try:
            os.makedirs("data/assessments", exist_ok=True)
            filename = f"data/assessments/{self.system_state['session_id']}_证据_思维.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"📄 评估报告已保存: {filename}")
        except Exception as e:
            print(f"⚠️ 保存报告时出错: {e}")

    def _save_user_score_summary(self, total_score: int):
        """保存用户评分汇总CSV（线程安全版本）

        格式: 编号,姓名,维度1,维度2,维度3,维度4,维度5,维度6,维度7,总分

        注意：使用全局文件锁保护，支持并发写入
        """
        try:
            # 如果没有用户信息，跳过保存
            if not self.user_id or not self.user_name:
                return

            os.makedirs("data", exist_ok=True)
            score_file = "data/user_scores.csv"

            # 提取各维度分数
            dim_scores = []
            for dim_id in range(1, 8):
                score = self.system_state["dimension_scores"].get(dim_id, {}).get("score", 0)
                dim_scores.append(score)

            # 准备行数据
            row_data = {
                "编号": self.user_id,
                "姓名": self.user_name,
                "维度1": dim_scores[0],
                "维度2": dim_scores[1],
                "维度3": dim_scores[2],
                "维度4": dim_scores[3],
                "维度5": dim_scores[4],
                "维度6": dim_scores[5],
                "维度7": dim_scores[6],
                "总分": total_score
            }

            # ⚡ 使用全局锁保护文件写入（支持并发）
            with _USER_SCORES_LOCK:
                # 检查文件是否存在（必须在锁内检查）
                file_exists = os.path.exists(score_file)

                # 写入CSV
                with open(score_file, 'a', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ["编号", "姓名", "维度1", "维度2", "维度3", "维度4", "维度5", "维度6", "维度7", "总分"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)

                    # 如果文件不存在，先写入表头
                    if not file_exists:
                        writer.writeheader()

                    # 写入数据行
                    writer.writerow(row_data)

            print(f"📊 用户评分已保存到: {score_file}")

        except Exception as e:
            print(f"⚠️ 保存用户评分时出错: {e}")
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "status": self.system_state["status"],
            "session_id": self.system_state["session_id"],
            "current_dimension": self.system_state.get("current_dimension"),
            "completed_dimensions": len(self.system_state["dimension_scores"]),
            "total_interactions": len(self.system_state["interactions"]),
            "current_dimension_name": self.current_work_state.get("dimension_info", {}).get("dimension_name")
        }
    
    def force_score_current_dimension(self) -> Dict:
        """强制对当前维度评分（用于测试或特殊情况）"""
        if len(self.system_state["user_responses"]) == 0:
            return {"error": "没有用户回应，无法评分"}
        
        # 创建虚拟诊断结果
        fake_diagnostic = {
            "sufficient": True,
            "reason": "强制评分",
            "recommendation": "score",
            "confidence": 0.5
        }
        
        return self._score_current_dimension(fake_diagnostic)

# CLI接口
class CCTDICommandLineInterface:
    """命令行界面"""
    
    def __init__(self):
        self.system = CCTDIAssessmentSystem()
        
    def run(self):
        """运行命令行界面"""
        print("=" * 60)
        print("🧠 CCTDI 批判性思维评估系统")
        print("=" * 60)
        
        # 开始评估
        start_result = self.system.start_assessment()
        print(f"\n{start_result['message']}")
        print(f"📖 当前维度: {start_result['current_dimension']} ({start_result['dimension_progress']})")
        print(f"\n维度指导:\n{start_result['guidance']}")
        print(f"\n❓ {start_result['first_question']}")
        
        # 主交互循环
        while self.system.system_state["status"] == "running":
            try:
                user_input = input("\n👤 您的回答: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("👋 评估已退出")
                    break
                
                if not user_input:
                    print("⚠️ 请输入您的回答")
                    continue
                
                # 处理用户回应
                result = self.system.process_user_response(user_input)
                
                if result.get("status") == "continue":
                    print(f"\n🤖 [{result['interaction_mode']}模式] {result['next_question']}")
                    
                elif result.get("status") == "dimension_completed":
                    prev = result["previous_dimension_result"]
                    new = result["new_dimension"]
                    print(f"\n✅ {prev['name']} 维度完成！得分: {prev['score']}分 ({prev['level']})")
                    print(f"\n📖 开始新维度: {new['name']} ({result['progress']})")
                    print(f"\n维度指导:\n{new['guidance']}")
                    print(f"\n❓ {new['first_question']}")
                    
                elif result.get("status") == "completed":
                    print("\n🎉 恭喜！所有维度评估完成！")
                    print(f"\n📊 最终结果:")
                    print(f"总分: {result['total_score']}/420 分")
                    print(f"平均分: {result['average_score']} 分")
                    print(f"总体评级: {result['overall_level']}")
                    print(f"\n各维度得分:")
                    for dim_id, score_info in result["dimension_scores"].items():
                        print(f"  {score_info['dimension']}: {score_info['score']}分 ({score_info['level']})")
                    break
                    
                elif "error" in result:
                    print(f"❌ 错误: {result['error']}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 评估已中断")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")

# 测试和主函数
if __name__ == "__main__":
    print("🧪 测试CCTDI评估系统...")
    
    # 可以选择运行CLI或者简单测试
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        # 运行CLI界面
        cli = CCTDICommandLineInterface()
        cli.run()
    else:
        # 简单测试
        try:
            system = CCTDIAssessmentSystem()
            
            # 测试开始评估
            start_result = system.start_assessment()
            print("✅ 评估开始成功")
            print(f"当前维度: {start_result['current_dimension']}")
            print(f"首个问题: {start_result['first_question']}")
            
            # 测试系统状态
            status = system.get_system_status()
            print(f"✅ 系统状态: {status}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
