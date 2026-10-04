from .md2doc import MarkdownToWordConverter
from core.models import Article
from core.db import DB
from datetime import datetime, timezone
import json
import csv
import zipfile
import os
from core.print import print_success,print_error
from jobs.notice import sys_notice

def process_single_article(art, add_title, remove_images, remove_links, export_md, 
                          export_docx, export_json, export_csv, export_pdf, 
                          docx_path, writer):
    """
    处理单篇文章的导出逻辑
    重构：
    - export_docx 使用 pdf2docx 转换（先生成 PDF，再转为 DOCX）
    - export_md 使用 html2doc (html2markdown) 转换
    - export_pdf 使用原有的 PDF 转换
    返回是否成功处理
    """
    from core.content_format import format_content
    from core.common.file_tools import sanitize_filename
    
    # 检查是否需要导出任何格式的文件
    if not (export_md or export_docx or export_json or export_csv or export_pdf):
        return False
    
    print(art.id, art.title, art.id)
    
    # 生成文件名
    name = datetime.fromtimestamp(art.publish_time, tz=timezone.utc).strftime("%Y%m%d") + "_" + art.title
    filename = sanitize_filename(name) + ".docx"
    json_filename = sanitize_filename(name) + ".json"
    md_filename = sanitize_filename(name) + ".md"
    pdf_filename = sanitize_filename(name) + ".pdf"
    
    # JSON 内容
    json_content = {
        "id": art.id,
        "url": art.url,
        "title": art.title,
        "pic_url": art.pic_url,
        "description": art.description,
        "status": art.status,
        "publish_time": art.publish_time
    }
    
    try:
        # 获取文章 HTML 内容
        html_content = art.content if hasattr(art, 'content') and art.content else ""
        
        # 步骤1: 导出 Markdown（使用 html2doc）
        md_generated = False
        if export_md and html_content:
            try:
                from tools.mdtools.html2doc import html_to_markdown_file
                
                md_full_path = f"{docx_path}{md_filename}"
                
                # 配置选项
                config = {
                    'remove_images': remove_images,
                    'remove_links': remove_links,
                }
                
                # 转换 HTML 为 Markdown
                document_title = art.title if add_title else None
                success = html_to_markdown_file(html_content, md_full_path, document_title, config)
                
                if success:
                    print_success(f"Markdown文件已生成: {md_filename}")
                    md_generated = True
                else:
                    print_error(f"Markdown文件生成失败: {md_filename}")
                    
            except ImportError as e:
                print_error(f"html2doc依赖缺失: {e}")
            except Exception as e:
                print_error(f"HTML转Markdown失败: {e}")
        
        # 步骤2: 生成 PDF（如果需要导出 DOCX 或 PDF）
        pdf_generated = False
        if export_docx or export_pdf:
            try:
                from tools.mdtools.pdf import url_to_pdf
                pdf_full_path = f"{docx_path}{pdf_filename}"
                from core.config import cfg
                browser_type = cfg.get("gather.browser_type", "webkit")
                port=cfg.get("port","8001")
                url=art.url if art.content =="" else f"http://127.0.0.1:{port}/views/print/{art.id}"
                url_to_pdf(url, pdf_full_path, browser_type=str(browser_type))
                
                # 验证PDF文件是否生成
                if not os.path.exists(pdf_full_path):
                    raise RuntimeError(f"PDF文件生成失败: {pdf_full_path}")
                
                print_success(f"PDF文件已生成: {pdf_filename}")
                pdf_generated = True
                
            except ImportError as e:
                print_error(f"PDF转换依赖缺失: {e}")
            except Exception as e:
                print_error(f"PDF转换失败: {e}")
        
        # 步骤3: 导出 DOCX（使用 pdf2docx）
        docx_generated = False
        if export_docx and pdf_generated:
            try:
                from tools.mdtools.pdf_extractor import pdf_to_docx
                
                pdf_full_path = f"{docx_path}{pdf_filename}"
                docx_full_path = f"{docx_path}{filename}"
                
                # 从 PDF 转换为 DOCX（优先使用 pdf2docx 库）
                success = pdf_to_docx(pdf_full_path, docx_full_path)
                
                if success:
                    print_success(f"DOCX文件已生成: {filename}")
                    docx_generated = True
                else:
                    print_error(f"DOCX文件生成失败: {filename}")
                    
            except ImportError as e:
                print_error(f"pdf2docx依赖缺失: {e}")
            except Exception as e:
                print_error(f"PDF转DOCX失败: {e}")
        
        # 步骤4: 保存 JSON 文件（如果需要）
        json_generated = False
        if export_json:
            try:
                json_full_path = f"{docx_path}{json_filename}"
                with open(json_full_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(json_content, ensure_ascii=False, indent=2))
                json_generated = True
            except Exception as e:
                print_error(f"JSON文件保存失败: {e}")
        
        # 步骤5: 记录到 CSV（如果需要）
        csv_generated = False
        if export_csv and writer:
            try:
                writer.writerow([
                    art.title, 
                    art.url, 
                    datetime.fromtimestamp(art.publish_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                ])
                csv_generated = True
            except Exception as e:
                print_error(f"CSV记录失败: {e}")
        
        # 汇总导出结果
        exported_files = []
        if json_generated: exported_files.append("JSON")
        if md_generated: exported_files.append("MD")
        if docx_generated: exported_files.append("DOCX")
        if pdf_generated: exported_files.append("PDF")
        if csv_generated: exported_files.append("CSV")
        
        if exported_files:
            print_success(f"文件已保存: {', '.join(exported_files)} - {name}")
            return True
        else:
            print_error(f"没有文件被成功导出: {name}")
            return False
            
    except Exception as e:
        print_error(f"保存文档失败: {e}")
        return False

def process_articles(session, mp_id=None,doc_id=None, page_size=10, page_count=1, add_title=True, document_id=None,
                    remove_images=False, remove_links=False, export_md=True, 
                    export_docx=True, export_json=True, export_csv=True, export_pdf=True,
                    docx_path="./data/docs/", writer=None):
    """
    处理文章数据的核心函数
    返回处理的文章数量
    """
    record_count = 0
    i = 0
    is_break=False
    while True:
        if is_break:
            break
        if page_count != 0 and i >= page_count:
            break
            
        query = session.query(Article).filter(Article.content != None).where(Article.status == 1)
        if mp_id:
            query = query.where(Article.mp_id.in_(mp_id.split(",")))
        if doc_id:
            query = query.where(Article.id.in_(doc_id))
            is_break=True   

        query = query.order_by(Article.publish_time.desc(), Article.id.desc())
        if is_break==False:
            query=query.offset(i * page_size).limit(page_size)
        i = i + 1
        arts = query.all()
        
        if arts is None or len(arts) == 0:
            break
            
        for art in arts:
            if process_single_article(art, add_title, remove_images, remove_links, 
                                    export_md, export_docx, export_json, export_csv, 
                                    export_pdf, docx_path, writer):
                record_count += 1
    
    return record_count

def export_md_to_doc(mp_id:str=None,doc_id:list=None,page_size:int=10,page_count:int=1,add_title=True,remove_images:bool=True,remove_links:bool=False
                     ,export_md:bool=False,export_docx:bool=False,export_json:bool=False,export_csv:bool=False,export_pdf:bool=True,domain="",zip_filename=None,zip_file=True):
    session = DB.get_session()
    if mp_id==None:
        raise ValueError("公众号ID不能为空")
    docx_path = f"./data/docs/{mp_id}/"
    if not os.path.exists(docx_path):
        os.makedirs(docx_path)
    csv_filename = f"{docx_path}articles.csv"
    
    # 初始化CSV文件和writer（仅在需要导出CSV时）
    csv_file = None
    writer = None
    if export_csv:
        csv_file = open(csv_filename, "w", newline="", encoding="utf-8")
        writer = csv.writer(csv_file)
        writer.writerow(["标题", "链接", "发布时间"])
    
    # 调用独立的文章处理函数
    record_count = process_articles(
        session=session,
        mp_id=mp_id,
        doc_id=doc_id,
        page_size=page_size,
        page_count=page_count,
        add_title=add_title,
        remove_images=remove_images,
        remove_links=remove_links,
        export_md=export_md,
        export_docx=export_docx,
        export_json=export_json,
        export_csv=export_csv,
        export_pdf=export_pdf,
        docx_path=docx_path,
        writer=writer
    )
    
    # 关闭CSV文件（如果打开了）
    if csv_file:
        csv_file.close()
        print_success(f"CSV 文件已保存为 {csv_filename}")
    
    # 打包所有导出的文件为zip并删除源文件
    if record_count > 0:
        if not zip_filename:
            zip_filename = f"{docx_path}exported_articles_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
        else:
            zip_filename = f"{docx_path}{zip_filename}"
            if not zip_filename.endswith('.zip'):
                zip_filename += '.zip'
        if zip_file==False:
            exported_files=[]
            for root, dirs, files in os.walk(docx_path):
                    for file in files:
                        print_success(f"导出文件: {os.path.join(root, file)}")
                        exported_files.append(os.path.join(root, file))
            return exported_files
        try:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历导出目录中的所有文件
                for root, dirs, files in os.walk(docx_path):
                    for file in files:
                        # 跳过所有zip文件，包括正在创建的zip文件
                        if file.endswith('.zip'):
                            continue
                        file_path = os.path.join(root, file)
                        # 添加文件到zip，使用相对路径
                        arc_name = os.path.relpath(file_path, docx_path)
                        zipf.write(file_path, arc_name)
                        # 删除源文件
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print_error(f"删除文件失败 {file_path}: {e}")
            
            print_success(f"所有文件已打包为: {zip_filename}")
            print_success(f"源文件已删除")
            
            # 发送系统通知，包含下载链接
            download_link = domain + docx_path + zip_filename.split('/')[-1]
            print_success(f"转换完成{download_link}")
            sys_notice(f"文章导出完成！共处理 {record_count} 篇文章。下载链接: [点击下载]({download_link})")
        except Exception as e:
            print_error(f"打包文件失败: {e}")
    
    print_success(f"导出完成，共处理 {record_count} 篇文章")