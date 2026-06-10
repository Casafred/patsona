"""CLI 入口模块 - 基于 Typer 的命令行界面"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from patsona.classifier.engine import ClassificationEngine
from patsona.config import settings
from patsona.preprocessor.parser import PatentParser
from patsona.reporter.formatter import format_single, format_batch, format_markdown
from patsona.reporter.stats import BatchStats
from patsona.rules.loader import RuleLoader
from patsona.sample.excel_loader import ExcelSampleLoader

app = typer.Typer(
    name="patsona",
    help="专利细分分类系统 - 轻量化本地工具，调用大模型API完成专利分类",
    no_args_is_help=True,
)
console = Console()


@app.command()
def classify(
    text: str = typer.Argument(..., help="待分类的专利文本"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="覆盖默认LLM模型"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径（Markdown格式）"),
) -> None:
    """直接对粘贴的专利文本进行分类"""
    console.print(Panel(f"[bold blue]正在分类专利文本...[/]", title="Patsona 分类"))

    # 加载规则
    rules = _load_rules()
    if not rules:
        console.print("[bold red]错误：未加载到任何分类规则，请检查 rules/ 目录[/]")
        raise typer.Exit(1)

    # 解析文本
    parser = PatentParser()
    patent_doc = parser.parse_text(text)

    # 执行分类
    engine = ClassificationEngine(model_override=model)
    result = engine.classify(patent_doc, rules)

    # 输出结果
    formatted = format_single(result)
    console.print(formatted)

    # 可选写入文件
    if output:
        Path(output).write_text(format_markdown([result]), encoding="utf-8")
        console.print(f"[green]结果已写入 {output}[/]")


@app.command(name="classify-file")
def classify_file(
    file_path: Path = typer.Argument(..., help="专利文件路径（支持 PDF/DOCX/TXT）", exists=True),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="覆盖默认LLM模型"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
) -> None:
    """从文件读取专利内容并分类"""
    console.print(Panel(f"[bold blue]正在解析文件: {file_path}[/]", title="Patsona 分类"))

    # 解析文件
    parser = PatentParser()
    patent_doc = parser.parse_file(file_path)
    console.print(f"[dim]标题: {patent_doc.title or '(未识别)'}[/dim]")

    # 加载规则并分类
    rules = _load_rules()
    if not rules:
        console.print("[bold red]错误：未加载到任何分类规则[/]")
        raise typer.Exit(1)

    engine = ClassificationEngine(model_override=model)
    result = engine.classify(patent_doc, rules)

    formatted = format_single(result)
    console.print(formatted)

    if output:
        Path(output).write_text(format_markdown([result]), encoding="utf-8")
        console.print(f"[green]结果已写入 {output}[/]")


@app.command(name="classify-batch")
def classify_batch(
    directory: Path = typer.Argument(..., help="包含专利文件的目录", exists=True),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="覆盖默认LLM模型"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    pattern: str = typer.Option("*.pdf", "--pattern", "-p", help="文件匹配模式"),
) -> None:
    """批量分类目录下的专利文件"""
    console.print(Panel(f"[bold blue]批量分类: {directory}[/]", title="Patsona 批量分类"))

    # 收集文件
    files = list(directory.glob(pattern))
    if not files:
        # 尝试其他格式
        for ext in ["*.docx", "*.txt", "*.pdf", "*.PDF", "*.DOCX"]:
            files.extend(directory.glob(ext))
        files = list(set(files))

    if not files:
        console.print(f"[yellow]目录 {directory} 中未找到专利文件[/]")
        raise typer.Exit(0)

    console.print(f"[dim]找到 {len(files)} 个文件[/]")

    # 加载规则
    rules = _load_rules()
    if not rules:
        console.print("[bold red]错误：未加载到任何分类规则[/]")
        raise typer.Exit(1)

    # 逐文件分类
    parser = PatentParser()
    engine = ClassificationEngine(model_override=model)
    results = []

    for i, file_path in enumerate(files, 1):
        console.print(f"\n[bold]({i}/{len(files)})[/] {file_path.name}")
        try:
            patent_doc = parser.parse_file(file_path)
            result = engine.classify(patent_doc, rules)
            results.append(result)
        except Exception as e:
            console.print(f"[red]  解析失败: {e}[/]")

    # 输出统计
    stats = BatchStats()
    stats_report = stats.compute(results)
    console.print(stats_report)

    # 输出批量结果
    formatted = format_batch(results)
    console.print(formatted)

    if output:
        Path(output).write_text(format_markdown(results), encoding="utf-8")
        console.print(f"[green]结果已写入 {output}[/]")


@app.command(name="import-samples")
def import_samples(
    excel_path: Path = typer.Argument(..., help="Excel样本文件路径", exists=True),
    sheet: Optional[str] = typer.Option(None, "--sheet", "-s", help="工作表名称"),
) -> None:
    """从Excel导入分类样本数据"""
    console.print(Panel(f"[bold blue]导入样本: {excel_path}[/]", title="Patsona 样本导入"))

    loader = ExcelSampleLoader()
    samples = loader.load(excel_path, sheet_name=sheet)

    console.print(f"[green]成功导入 {len(samples)} 条样本[/]")

    # 展示前5条预览
    table = Table(title="样本预览（前5条）")
    table.add_column("专利号", style="cyan")
    table.add_column("标题", style="white")
    table.add_column("分类", style="green")

    for sample in samples[:5]:
        table.add_row(sample.patent_id, sample.title[:40], sample.branch_id)

    console.print(table)


@app.command(name="check-rules")
def check_rules() -> None:
    """校验分类规则的完整性和一致性"""
    console.print(Panel("[bold blue]校验分类规则...[/]", title="Patsona 规则校验"))

    loader = RuleLoader()
    rules_dir = settings.rules_path

    if not rules_dir.exists():
        console.print(f"[red]规则目录不存在: {rules_dir}[/]")
        raise typer.Exit(1)

    # 加载并校验
    branches, errors = loader.load_and_validate(rules_dir)

    if errors:
        console.print(f"[bold red]发现 {len(errors)} 个错误:[/]")
        for err in errors:
            console.print(f"  [red]✗[/] {err}")
    else:
        console.print(f"[green]✓ 所有规则校验通过，共 {len(branches)} 个技术分支[/]")

    # 展示分类树概览
    if branches:
        from patsona.rules.tree import ClassificationTree

        tree = ClassificationTree()
        tree.build(branches)
        tree_summary = tree.summary()
        console.print(tree_summary)


@app.command(name="analyze-claims")
def analyze_claims(
    file_path: Optional[Path] = typer.Option(None, "--file", "-f", help="专利文件路径（PDF/DOCX/TXT）"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="直接粘贴权利要求文本"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="覆盖默认LLM模型"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径（Markdown格式）"),
) -> None:
    """分析独立权利要求：识别独权/从权，对比各独权异同，标识异常独权"""
    console.print(Panel("[bold blue]独立权利要求分析[/]", title="Patsona 独权分析"))

    # 获取权利要求文本
    claims_text = ""

    if file_path:
        if not file_path.exists():
            console.print(f"[red]文件不存在: {file_path}[/]")
            raise typer.Exit(1)
        parser = PatentParser()
        patent_doc = parser.parse_file(file_path)
        # 优先使用权利要求，其次使用全文
        claims_text = "\n".join(patent_doc.claims) if patent_doc.claims else patent_doc.full_text
    elif text:
        claims_text = text
    else:
        console.print("[red]请通过 --file 或 --text 提供权利要求文本[/]")
        raise typer.Exit(1)

    if not claims_text.strip():
        console.print("[red]未获取到有效的权利要求文本[/]")
        raise typer.Exit(1)

    # 执行分析
    from patsona.analyzer.claim_analyzer import ClaimAnalyzer
    from patsona.analyzer.formatter import format_claim_analysis, format_claim_analysis_markdown

    analyzer = ClaimAnalyzer(model_override=model)
    result = analyzer.analyze(claims_text)

    # 输出结果
    formatted = format_claim_analysis(result)
    console.print(formatted)

    # 可选写入文件
    if output:
        md_text = format_claim_analysis_markdown(result)
        Path(output).write_text(md_text, encoding="utf-8")
        console.print(f"[green]结果已写入 {output}[/]")


def _load_rules() -> list:
    """加载分类规则，返回技术分支列表"""
    loader = RuleLoader()
    rules_dir = settings.rules_path
    if not rules_dir.exists():
        return []
    branches, _ = loader.load_and_validate(rules_dir)
    return branches


if __name__ == "__main__":
    app()
