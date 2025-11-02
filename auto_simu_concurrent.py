"""
自动化CCTDI评估模拟脚本 - 并发版本
使用多线程并发执行，大幅缩短批量测试时间

特点:
- 使用ThreadPoolExecutor实现并发
- 线程安全的文件写入
- 实时进度追踪
- 异常隔离处理

使用方法:
    批量测试(默认3线程): python auto_simu_并发.py
    自定义线程数: python auto_simu_并发.py --workers 5
    单个用户测试: python auto_simu_并发.py persons/1张伟.txt
"""
import os
import sys
import json
import time
import threading
import argparse
from datetime import datetime
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
from cctdi_system import CCTDIAssessmentSystem

# 加载环境变量
load_dotenv()

# 全局文件锁 - 保护 user_scores.csv 的并发写入
CSV_LOCK = threading.Lock()
# 全局打印锁 - 防止控制台输出混乱
PRINT_LOCK = threading.Lock()


def thread_safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with PRINT_LOCK:
        print(*args, **kwargs)


class VirtualUser:
    """虚拟用户 - 读取画像文件并使用LLM生成回答"""

    def __init__(self, persona_file_path: str, quiet: bool = False):
        """初始化虚拟用户

        Args:
            persona_file_path: 画像文件路径
            quiet: 是否静默模式（减少输出）
        """
        self.persona_file_path = persona_file_path
        self.persona_content = self._load_persona(persona_file_path)
        self.name = self._extract_name()
        self.quiet = quiet

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')

        if not quiet:
            thread_safe_print(f"✅ 虚拟用户已加载: {self.name}")

    def _load_persona(self, file_path: str) -> str:
        """读取用户画像文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            thread_safe_print(f"❌ 读取画像文件失败: {e}")
            sys.exit(1)

    def _extract_name(self) -> str:
        """从画像中提取姓名"""
        lines = self.persona_content.split('\n')
        for line in lines:
            if '姓名' in line or '名字' in line:
                # 尝试提取中文名字
                parts = line.split('：')
                if len(parts) > 1:
                    name_part = parts[1].strip()
                    # 提取第一个词（中文名）
                    name = name_part.split()[0]
                    return name
        return "虚拟用户"

    def generate_response(self, question: str, dimension: str,
                         round_num: int, history: list = None) -> str:
        """
        根据用户画像和问题生成回答

        Args:
            question: 系统提出的问题
            dimension: 当前评估维度
            round_num: 当前轮次
            history: 之前的对话历史 (可选)

        Returns:
            生成的回答文本
        """
        # 构建对话历史
        history_text = ""
        if history:
            history_text = "\n".join([
                f"问: {h['question']}\n答: {h['answer']}"
                for h in history[-2:]  # 只包含最近2轮
            ])

        # 构建系统提示词
        system_prompt = f"""
你正在扮演以下这个人参加CCTDI批判性思维评估:

{self.persona_content}

当前评估情境:
- 当前维度: {dimension}
- 当前是第{round_num}轮对话

{f"之前的对话:{history_text}" if history_text else ""}

系统问题: {question}

请完全按照上述人物画像中的性格特征、思维方式、语言风格来回答这个问题。

回答要求:
- 长度: 30-100字（简短回答，不要过长）
- 口语化，像普通人说话，不要过于书面化或学术化
- 可以有不确定的表达，如"嗯...""可能""不太清楚""我觉得吧"
- 不要过于深刻和完美，要有普通人的局限性和不完整性
- 避免过度条理化的回答（不要总是123列点，要自然随意）
- 可以有口语停顿、重复、不完整的句子
- 不要提及"我在扮演"、"根据画像"等元描述
- 直接以第一人称回答

请给出你的回答:
"""

        try:
            # 调用LLM生成回答
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt}
                ],
                temperature=0.95,
                max_tokens=200
            )

            answer = response.choices[0].message.content.strip()
            return answer

        except Exception as e:
            thread_safe_print(f"⚠️ [{self.name}] 生成回答时出错: {e}")
            # 返回一个简单的默认回答
            return f"我认为这个问题需要从多个角度来思考。（生成失败的默认回答）"


class SimulationRunner:
    """自动化模拟运行器"""

    def __init__(self, persona_file_path: str, quiet: bool = False):
        """初始化模拟运行器

        Args:
            persona_file_path: 画像文件路径
            quiet: 是否静默模式（并发时使用）
        """
        self.quiet = quiet

        if not quiet:
            thread_safe_print("=" * 60)
            thread_safe_print("🎯 CCTDI自动化评估模拟")
            thread_safe_print("=" * 60)
            thread_safe_print(f"\n📄 虚拟用户画像: {persona_file_path}")

        # 创建虚拟用户
        self.virtual_user = VirtualUser(persona_file_path, quiet=quiet)

        # 从文件名提取编号和姓名
        user_id, user_name = self._extract_user_info(persona_file_path)
        self.user_id = user_id
        self.user_name = user_name

        # 创建评估系统
        if not quiet:
            thread_safe_print(f"🔧 初始化评估系统...")
        self.system = CCTDIAssessmentSystem(user_id=user_id, user_name=user_name)

        # 记录对话历史（用于上下文）
        self.conversation_history = []

        if not quiet:
            thread_safe_print(f"✅ 系统准备完成 (编号:{user_id}, 姓名:{user_name})\n")

    def _extract_user_info(self, persona_file_path: str) -> tuple:
        """从文件名提取编号和姓名

        文件名格式: persons/4陈思远.txt
        提取: 编号=4, 姓名=陈思远

        Returns:
            (编号, 姓名)
        """
        try:
            # 获取文件名（去掉路径和扩展名）
            filename = os.path.basename(persona_file_path)  # "4陈思远.txt"
            name_without_ext = os.path.splitext(filename)[0]  # "4陈思远"

            # 分离编号和姓名
            # 假设编号是开头的数字
            user_id = ""
            user_name = ""

            for i, char in enumerate(name_without_ext):
                if char.isdigit():
                    user_id += char
                else:
                    # 剩余部分是姓名
                    user_name = name_without_ext[i:]
                    break

            # 如果没有提取到，使用默认值
            if not user_id:
                user_id = "0"
            if not user_name:
                user_name = "未知用户"

            return user_id, user_name

        except Exception as e:
            thread_safe_print(f"⚠️ 提取用户信息失败: {e}")
            return "0", "未知用户"

    def run(self) -> Dict:
        """运行完整的7个维度评估

        Returns:
            评估结果字典
        """
        start_time = time.time()

        # 开始评估
        start_result = self.system.start_assessment()

        if not self.quiet:
            thread_safe_print("=" * 60)
            thread_safe_print(f"📊 维度 1/7: {start_result['current_dimension']}")
            thread_safe_print("=" * 60)
            thread_safe_print(f"\n💡 维度说明:\n{start_result['guidance'][:200]}...\n")

        # 显示第一个问题
        current_question = start_result['first_question']
        if not self.quiet:
            thread_safe_print(f"💬 [第1轮] 系统提问:\n{current_question}\n")

        # 记录当前维度的历史
        current_dimension_history = []
        round_num = 1

        # 主循环
        while self.system.system_state["status"] == "running":
            try:
                # 生成虚拟用户的回答
                if not self.quiet:
                    thread_safe_print(f"🤔 虚拟用户 {self.virtual_user.name} 正在思考...")
                    time.sleep(0.5)  # 模拟思考时间（并发时减少）

                answer = self.virtual_user.generate_response(
                    question=current_question,
                    dimension=self.system.current_work_state["dimension_info"]["dimension_name"],
                    round_num=round_num,
                    history=current_dimension_history
                )

                if not self.quiet:
                    thread_safe_print(f"💭 回答:\n{answer}\n")

                # 记录对话历史
                current_dimension_history.append({
                    'question': current_question,
                    'answer': answer
                })

                # 提交回答给系统
                result = self.system.process_user_response(answer)

                # 处理系统响应
                if result.get("status") == "continue":
                    # 继续当前维度的对话
                    round_num += 1
                    current_question = result['next_question']
                    if not self.quiet:
                        thread_safe_print(f"💬 [第{round_num}轮] 系统提问:\n{current_question}\n")

                elif result.get("status") == "dimension_completed":
                    # 当前维度完成，进入下一个维度
                    prev = result["previous_dimension_result"]
                    new = result["new_dimension"]

                    if not self.quiet:
                        thread_safe_print("─" * 60)
                        thread_safe_print(f"✅ 维度完成！得分: {prev['score']}分 ({prev['level']})")
                        thread_safe_print("─" * 60)
                        thread_safe_print()

                        # 显示下一个维度
                        thread_safe_print("=" * 60)
                        thread_safe_print(f"📊 维度 {result['progress']}: {new['name']}")
                        thread_safe_print("=" * 60)
                        thread_safe_print(f"\n💡 维度说明:\n{new['guidance'][:200]}...\n")

                    # 重置维度历史
                    current_dimension_history = []
                    round_num = 1
                    current_question = new['first_question']
                    if not self.quiet:
                        thread_safe_print(f"💬 [第1轮] 系统提问:\n{current_question}\n")

                elif result.get("status") == "completed":
                    # 所有维度完成
                    if not self.quiet:
                        thread_safe_print("=" * 60)
                        thread_safe_print("🎉 评估完成！")
                        thread_safe_print("=" * 60)
                        thread_safe_print(f"\n📊 最终结果:")
                        thread_safe_print(f"总分: {result['total_score']}/420 分")
                        thread_safe_print(f"平均分: {result['average_score']} 分")
                        thread_safe_print(f"总体评级: {result['overall_level']}")

                        thread_safe_print(f"\n📋 各维度得分:")
                        for dim_id, score_info in result["dimension_scores"].items():
                            thread_safe_print(f"  {score_info['dimension']}: {score_info['score']}分 ({score_info['level']})")

                        # 显示生成的文件
                        thread_safe_print(f"\n📄 生成的文件:")
                        csv_file = self.system.csv_manager.csv_file
                        json_file = f"data/assessments/{self.system.system_state['session_id']}_证据_思维.json"
                        score_file = "data/user_scores.csv"
                        thread_safe_print(f"  CSV对话记录: {csv_file}")
                        thread_safe_print(f"  JSON评估报告: {json_file}")
                        thread_safe_print(f"  📊 用户评分汇总: {score_file}")

                    # 返回结果
                    elapsed_time = time.time() - start_time
                    return {
                        "user_id": self.user_id,
                        "user_name": self.user_name,
                        "total_score": result['total_score'],
                        "average_score": result['average_score'],
                        "overall_level": result['overall_level'],
                        "elapsed_time": elapsed_time,
                        "success": True
                    }

                elif "error" in result:
                    thread_safe_print(f"❌ [{self.user_name}] 错误: {result['error']}")
                    return {
                        "user_id": self.user_id,
                        "user_name": self.user_name,
                        "error": result['error'],
                        "success": False
                    }

            except KeyboardInterrupt:
                thread_safe_print(f"\n\n⚠️ [{self.user_name}] 评估被用户中断")
                return {
                    "user_id": self.user_id,
                    "user_name": self.user_name,
                    "error": "用户中断",
                    "success": False
                }
            except Exception as e:
                thread_safe_print(f"❌ [{self.user_name}] 发生错误: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "user_id": self.user_id,
                    "user_name": self.user_name,
                    "error": str(e),
                    "success": False
                }

        # 显示运行时间
        elapsed_time = time.time() - start_time
        if not self.quiet:
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            thread_safe_print(f"\n⏱️ 总耗时: {minutes}分{seconds}秒")
            thread_safe_print("=" * 60)

        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "error": "未知错误",
            "success": False
        }


class ConcurrentBatchSimulationRunner:
    """并发批量自动化模拟运行器"""

    def __init__(self, persons_dir: str = "persons", max_workers: int = 3):
        """初始化并发批量模拟运行器

        Args:
            persons_dir: 画像文件目录
            max_workers: 最大并发线程数（默认3）
        """
        self.persons_dir = persons_dir
        self.max_workers = max_workers
        self.persona_files = self._scan_persona_files()

        if not self.persona_files:
            thread_safe_print(f"❌ {persons_dir} 目录下没有找到txt文件")
            sys.exit(1)

        thread_safe_print("=" * 60)
        thread_safe_print("🚀 CCTDI并发批量自动化评估模拟")
        thread_safe_print("=" * 60)
        thread_safe_print(f"📂 发现 {len(self.persona_files)} 个虚拟用户待测试")
        thread_safe_print(f"⚡ 并发线程数: {max_workers}")
        thread_safe_print(f"💡 预计加速: {min(max_workers, len(self.persona_files))}倍\n")

    def _scan_persona_files(self) -> list:
        """扫描persons目录，获取所有txt文件"""
        if not os.path.exists(self.persons_dir):
            return []

        txt_files = [
            os.path.join(self.persons_dir, f)
            for f in os.listdir(self.persons_dir)
            if f.endswith('.txt')
        ]

        # 按文件名中的数字编号排序（自然排序）
        def extract_number(filepath):
            filename = os.path.basename(filepath)
            # 提取开头的数字
            num_str = ""
            for char in filename:
                if char.isdigit():
                    num_str += char
                else:
                    break
            return int(num_str) if num_str else 999  # 没有编号的放最后

        return sorted(txt_files, key=extract_number)

    def _run_single_user(self, persona_file: str, index: int, total: int) -> Dict:
        """运行单个用户的评估（线程任务）

        Args:
            persona_file: 画像文件路径
            index: 当前索引
            total: 总数

        Returns:
            评估结果字典
        """
        try:
            # 提取用户姓名用于显示
            filename = os.path.basename(persona_file)
            name_without_ext = os.path.splitext(filename)[0]

            thread_safe_print(f"\n🔄 [{index}/{total}] 开始测试: {name_without_ext}")

            # 创建并运行单个用户的模拟（静默模式）
            runner = SimulationRunner(persona_file, quiet=True)
            result = runner.run()

            if result.get("success"):
                thread_safe_print(
                    f"✅ [{index}/{total}] {name_without_ext} 测试完成 - "
                    f"总分: {result['total_score']}/420 - "
                    f"耗时: {result['elapsed_time']:.1f}秒"
                )
            else:
                thread_safe_print(
                    f"❌ [{index}/{total}] {name_without_ext} 测试失败: {result.get('error', '未知错误')}"
                )

            return result

        except Exception as e:
            thread_safe_print(f"❌ [{index}/{total}] 测试 {name_without_ext} 时发生异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "user_name": name_without_ext,
                "error": str(e),
                "success": False
            }

    def run(self):
        """运行并发批量测试"""
        start_time = time.time()
        total_count = len(self.persona_files)
        completed_count = 0
        success_count = 0
        failed_count = 0
        results = []

        thread_safe_print(f"🚀 开始并发执行...\n")

        # 使用ThreadPoolExecutor并发执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self._run_single_user, persona_file, idx, total_count): persona_file
                for idx, persona_file in enumerate(self.persona_files, 1)
            }

            # 收集结果
            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1

                    if result.get("success"):
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    thread_safe_print(f"⚠️ 任务执行失败: {e}")
                    failed_count += 1
                    completed_count += 1

        # 显示批量测试汇总
        self._print_summary(completed_count, total_count, success_count, failed_count, start_time, results)

    def _print_summary(self, completed_count: int, total_count: int,
                      success_count: int, failed_count: int,
                      start_time: float, results: List[Dict]):
        """打印批量测试汇总"""
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        # 计算平均每人耗时
        avg_time_per_user = elapsed_time / completed_count if completed_count > 0 else 0

        # 计算加速比（假设顺序执行每人5分钟）
        sequential_time = completed_count * 5 * 60  # 假设每人5分钟
        speedup = sequential_time / elapsed_time if elapsed_time > 0 else 0

        thread_safe_print("\n" + "=" * 60)
        thread_safe_print("🎉 并发批量测试完成！")
        thread_safe_print("=" * 60)
        thread_safe_print(f"\n📊 测试统计:")
        thread_safe_print(f"  - 总测试人数: {completed_count}/{total_count}")
        thread_safe_print(f"  - 成功: {success_count} | 失败: {failed_count}")
        thread_safe_print(f"  - 总耗时: {minutes}分{seconds}秒 ({elapsed_time:.1f}秒)")
        thread_safe_print(f"  - 平均耗时: {avg_time_per_user:.1f}秒/人")
        thread_safe_print(f"  - 加速比: {speedup:.2f}x (相比顺序执行)")

        # 统计分数分布
        if results:
            successful_results = [r for r in results if r.get("success")]
            if successful_results:
                total_scores = [r["total_score"] for r in successful_results]
                avg_score = sum(total_scores) / len(total_scores)
                max_score = max(total_scores)
                min_score = min(total_scores)

                thread_safe_print(f"\n📈 分数统计:")
                thread_safe_print(f"  - 平均分: {avg_score:.1f}/420")
                thread_safe_print(f"  - 最高分: {max_score}/420")
                thread_safe_print(f"  - 最低分: {min_score}/420")

            thread_safe_print(f"\n📋 详细结果:")
            for result in sorted(results, key=lambda x: x.get("total_score", 0), reverse=True):
                if result.get("success"):
                    thread_safe_print(
                        f"  ✅ {result['user_name']}: "
                        f"{result['total_score']}/420 ({result['overall_level']}) - "
                        f"{result['elapsed_time']:.1f}秒"
                    )
                else:
                    thread_safe_print(f"  ❌ {result['user_name']}: 失败 - {result.get('error', '未知错误')}")

        thread_safe_print("\n📄 所有结果已保存到:")
        thread_safe_print(f"  - CSV对话记录: data/conversations/")
        thread_safe_print(f"  - JSON评估报告: data/assessments/")
        thread_safe_print(f"  - 用户评分汇总: data/user_scores.csv")
        thread_safe_print("=" * 60)


def main():
    """主函数"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        description="CCTDI批判性思维评估 - 并发自动化模拟",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  批量测试(默认3线程):  python auto_simu_并发.py
  自定义线程数:         python auto_simu_并发.py --workers 5
  单个用户测试:         python auto_simu_并发.py persons/1张伟.txt
        """
    )

    parser.add_argument(
        'persona_file',
        nargs='?',
        help='虚拟用户画像文件路径（可选，不指定则批量测试）'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=5,
        help='并发线程数（默认3，建议3-5）'
    )

    args = parser.parse_args()

    # 单个用户测试模式
    if args.persona_file:
        persona_file = args.persona_file

        # 检查文件是否存在
        if not os.path.exists(persona_file):
            thread_safe_print(f"❌ 文件不存在: {persona_file}")
            thread_safe_print("\n使用方法:")
            thread_safe_print("  批量测试: python auto_simu_并发.py --workers 5")
            thread_safe_print("  单个测试: python auto_simu_并发.py persons/用户画像.txt")
            sys.exit(1)

        # 创建并运行单个用户模拟器
        thread_safe_print(f"📌 单个用户测试模式\n")
        runner = SimulationRunner(persona_file, quiet=False)
        runner.run()

    # 批量并发测试模式
    else:
        thread_safe_print(f"📌 批量并发测试模式\n")

        # 验证并发数
        if args.workers < 1:
            thread_safe_print("⚠️ 并发线程数至少为1，已调整为1")
            args.workers = 1
        elif args.workers > 10:
            thread_safe_print("⚠️ 并发线程数过大可能触发API限制，建议不超过10")

        batch_runner = ConcurrentBatchSimulationRunner("persons", max_workers=args.workers)
        batch_runner.run()


if __name__ == "__main__":
    main()
