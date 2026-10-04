import re
import os
from typing import Any, Dict, List, Union
# """
# 模板引擎使用示例

# 基础用法:
# 1. 简单变量替换: {{variable}}
# 2. 条件判断: {% if condition %}...{% endif %}
# 3. 循环结构: {% for item in items %}...{% endfor %}
# """
class TemplateParser:
    """A lightweight template engine supporting variables, conditions and loops."""
    
    def __init__(self, template: str, template_dir: str = None):
        """Initialize the template parser with a template string."""
        self.template = template
        self.compiled = None
        self.custom_functions = {}
        self.template_dir = template_dir  # Template directory for include functionality
        
    def register_function(self, name: str, func: callable) -> None:
        """
        Register a custom function to be available in template expressions.
        
        Args:
            name: The name to use in templates
            func: The function to register
        """
        self.custom_functions[name] = func
        
    def register_functions(self, functions: Dict[str, callable]) -> None:
        """
        Register multiple custom functions at once.
        
        Args:
            functions: Dictionary of function names to functions
        """
        self.custom_functions.update(functions)

    def compile_template(self) -> None:
        """Compile the template into an intermediate representation."""
        # First process include directives
        processed_template = self._process_includes(self.template)
        
        # Split template into static parts and control blocks
        pattern = re.compile(
            r'(\{\%.*?\%\})|'  # control blocks {% ... %}
            r'(\{\{.*?\}\})'    # variables {{ ... }}
        )
        self.compiled = pattern.split(processed_template)
        
    def render(self, context: Dict[str, Any]) -> str:
        """
        Render the template with the given context.
        
        Args:
            context: A dictionary containing variables for template rendering
            
        Returns:
            The rendered template as a string
        """
        # Security check: validate context keys
        for key in context.keys():
            if not isinstance(key, str) or not key.isidentifier():
                raise ValueError(f"Invalid context key: {key}. Keys must be valid Python identifiers")
        
        if self.compiled is None:
            self.compile_template()
            
        output = []
        i = 0
        while i < len(self.compiled):
            part = self.compiled[i]
            
            if part is None:
                i += 1
                continue
                
            # Handle static text (preserve original formatting)
            if not (part.startswith('{{') or part.startswith('{%')):
                output.append(part)
                i += 1
                continue
                
            # Handle variables {{ var }} and nested {{ var.attr }} and eval expressions
            if part.startswith('{{') and part.endswith('}}'):
                # print(f"\nProcessing variable part: {part}")
                var_expr = part[2:-2].strip()
                # print(f"Extracted expression: {var_expr}")
                
                # Check if this is an eval expression (starts with =)
                if var_expr.startswith('='):
                    try:
                        # Evaluate the expression (after =)
                        expr = var_expr[1:]
                        result = self._evaluate_calculation(expr, context)
                        output.append(str(result))
                    except Exception as e:
                        output.append(f'[Error: {str(e)}]')
                elif ' or ' in var_expr:
                    # Handle 'or' operator for default values
                    parts = var_expr.split(' or ')
                    result = None
                    for part_expr in parts:
                        part_expr = part_expr.strip()
                        # Remove quotes if it's a literal string
                        if (part_expr.startswith('"') and part_expr.endswith('"')) or \
                           (part_expr.startswith("'") and part_expr.endswith("'")):
                            result = part_expr[1:-1]
                            break
                        else:
                            # Evaluate the variable
                            if '.' in part_expr:
                                # Handle nested attribute access
                                var_parts = part_expr.split('.')
                                current = context.get(var_parts[0], {})
                                for var_part in var_parts[1:]:
                                    if isinstance(current, dict):
                                        current = current.get(var_part, '')
                                    else:
                                        current = getattr(current, var_part, '')
                                    if current is None:
                                        current = ''
                                        break
                                value = current
                            else:
                                # Simple variable access
                                value = context.get(part_expr, '')
                            
                            # If value is not empty or not zero, use it
                            if value or value == 0:
                                result = value
                                break
                    
                    output.append(str(result if result is not None else ''))
                elif '.' in var_expr:
                    # print(f"DEBUG - Processing nested variable: {var_expr}")  # Debug
                    # Handle nested attribute access
                    parts = var_expr.split('.')
                    current = context.get(parts[0], {})
                    for part_name in parts[1:]:
                        if isinstance(current, dict):
                            current = current.get(part_name, '')
                        else:
                            current = getattr(current, part_name, '')
                        if current is None:
                            current = ''
                            break
                    output.append(str(current))
                else:
                    # Simple variable access
                    output.append(str(context.get(var_expr, '')))
                i += 1
                
            # Handle control blocks {% ... %}
            elif part.startswith('{%') and part.endswith('%}'):
                block = part[2:-2].strip()
                
                # Handle include directive (processed during compile, but keep for safety)
                if block.startswith('include '):
                    # Include should have been processed during compilation
                    i += 1
                    continue
                
                # Handle set variable
                if block.startswith('set '):
                    # Parse: set variable_name = expression
                    set_content = block[4:].strip()
                    if '=' in set_content:
                        var_name, value_expr = set_content.split('=', 1)
                        var_name = var_name.strip()
                        value_expr = value_expr.strip()
                        
                        # Evaluate the value expression
                        try:
                            if value_expr.startswith('='):
                                value_expr = value_expr[1:]
                            value = self._evaluate_calculation(value_expr, context)
                            # Store in context for future use
                            context[var_name] = value
                        except Exception as e:
                            context[var_name] = f"[Set Error: {str(e)}]"
                    i += 1
                    continue
                
                # Handle let variable
                if block.startswith('let '):
                    # Parse: let variable_name = expression
                    let_content = block[4:].strip()
                    if '=' in let_content:
                        var_name, value_expr = let_content.split('=', 1)
                        var_name = var_name.strip()
                        value_expr = value_expr.strip()
                        
                        # Evaluate the value expression
                        try:
                            if value_expr.startswith('='):
                                value_expr = value_expr[1:]
                            value = self._evaluate_calculation(value_expr, context)
                            # Store in context for current scope
                            context[var_name] = value
                        except Exception as e:
                            context[var_name] = f"[Let Error: {str(e)}]"
                    i += 1
                    continue
                
                # Handle if condition
                if block.startswith('if '):
                    condition = block[3:].strip()
                    result, updated_context = self._evaluate_condition(condition, context)
                    # Merge all variables except special ones and functions
                    for k, v in updated_context.items():
                        if not k.startswith('__') and k not in self.custom_functions:
                            # Only update context if the key doesn't exist or was modified
                            if k not in context or context[k] != v:
                                context[k] = v
                    # Ensure final_price is available in context if it was calculated
                    if 'final_price' in updated_context:
                        context['final_price'] = updated_context['final_price']
                    
                    # Find matching endif using helper method
                    endif_idx = self._skip_control_block(i, 'if', 'endif')
                    if endif_idx == len(self.compiled):
                        i += 1
                        continue
                    
                    # Find else if exists
                    else_idx = -1
                    for j in range(i+1, endif_idx):
                        part = self.compiled[j]
                        if isinstance(part, str) and part.strip() in ('{% else %}', 'else'):
                            else_idx = j
                            break
                    
                    # Process the appropriate block
                    if result:
                        # Process if block (from current position to else or endif)
                        end_idx = else_idx if else_idx != -1 else endif_idx
                        if_content = self.compiled[i+1:end_idx]
                        
                        if_parser = TemplateParser('')
                        if_parser.compiled = if_content
                        rendered = if_parser.render(context)
                        output.append(rendered)
                    elif else_idx != -1:
                        # Process else block
                        else_content = self.compiled[else_idx+1:endif_idx]
                        
                        else_parser = TemplateParser('')
                        else_parser.compiled = else_content
                        rendered = else_parser.render(context)
                        output.append(rendered)
                    
                    # Skip to after endif
                    i = endif_idx + 1
                    continue
                    
                # Handle for loop
                elif block.startswith('for ') and ' in ' in block:
                    loop_var, iterable = self._parse_for_block(block)
                    items = self._get_iterable(iterable, context)
                    
                    # Collect loop content
                    loop_content = []
                    j = i + 1
                    endfor_idx = j
                    while j < len(self.compiled):
                        inner_part = self.compiled[j]
                        if (isinstance(inner_part, str) and 
                            inner_part.startswith('{% endfor %}')):
                            endfor_idx = j
                            break
                        loop_content.append(str(inner_part) if inner_part else '')
                        j += 1
                        
                    # Render loop with preserved formatting and indentation
                    loop_output = []
                    total_items = len(items)
                    
                    # Get the indentation level from the template
                    for_line = self.compiled[i]
                    indent = ''
                    if isinstance(for_line, str):
                        indent_match = re.match(r'^(\s*)', for_line)
                        if indent_match:
                            indent = indent_match.group(1)
                    
                    for item_idx, item in enumerate(items):
                        loop_context = context.copy()
                        loop_context[loop_var] = item
                        
                        # Add loop variable with iteration info
                        loop_context['loop'] = {
                            'index': item_idx + 1,
                            'index0': item_idx,
                            'first': item_idx == 0,
                            'last': item_idx == total_items - 1,
                            'length': total_items,
                            'parentloop': context.get('loop')  # Save parent loop context
                        }
                        
                        # Render loop content with current item
                        item_output = []
                        j = 0
                        while j < len(loop_content):
                            part = loop_content[j]
                            if part is None:
                                j += 1
                                continue
                            
                            # Handle set/let statements inside for loop
                            if (isinstance(part, str) and 
                                part.startswith('{%') and 
                                part.endswith('%}')):
                                block = part[2:-2].strip()
                                
                                # Handle set variable
                                if block.startswith('set '):
                                    set_content = block[4:].strip()
                                    if '=' in set_content:
                                        var_name, value_expr = set_content.split('=', 1)
                                        var_name = var_name.strip()
                                        value_expr = value_expr.strip()
                                        
                                        # Evaluate value expression
                                        try:
                                            if value_expr.startswith('='):
                                                value_expr = value_expr[1:]
                                            value = self._evaluate_calculation(value_expr, loop_context)
                                            # Store in loop context
                                            loop_context[var_name] = value
                                        except Exception as e:
                                            loop_context[var_name] = f"[Set Error: {str(e)}]"
                                    
                                    j += 1
                                    continue
                                
                                # Handle let variable  
                                elif block.startswith('let '):
                                    let_content = block[4:].strip()
                                    if '=' in let_content:
                                        var_name, value_expr = let_content.split('=', 1)
                                        var_name = var_name.strip()
                                        value_expr = value_expr.strip()
                                        
                                        # Evaluate value expression
                                        try:
                                            if value_expr.startswith('='):
                                                value_expr = value_expr[1:]
                                            value = self._evaluate_calculation(value_expr, loop_context)
                                            # Store in loop context
                                            loop_context[var_name] = value
                                        except Exception as e:
                                            loop_context[var_name] = f"[Let Error: {str(e)}]"
                                    
                                    j += 1
                                    continue
                            
                            # Handle if conditions inside for loop
                            if (isinstance(part, str) and 
                                part.startswith('{% if ') and 
                                part.endswith('%}')):
                                condition = part[6:-2].strip()
                                result, _ = self._evaluate_condition(condition, loop_context)
                                
                                # Find matching endif
                                endif_idx = j + 1
                                nested_depth = 1
                                while endif_idx < len(loop_content):
                                    inner_part = loop_content[endif_idx]
                                    if (isinstance(inner_part, str) and 
                                        inner_part.startswith('{% if ') and 
                                        inner_part.endswith('%}')):
                                        nested_depth += 1
                                    elif (isinstance(inner_part, str) and 
                                          inner_part.startswith('{% endif %}')):
                                        nested_depth -= 1
                                        if nested_depth == 0:
                                            break
                                    endif_idx += 1
                                
                                # Process if block if condition is true
                                if result:
                                    if_content = loop_content[j+1:endif_idx]
                                    rendered = self._render_parts(if_content, loop_context)
                                    item_output.append(rendered)
                                
                                # Skip to after endif
                                j = endif_idx + 1
                            
                            # Handle variable references
                            elif isinstance(part, str) and part.startswith('{{') and part.endswith('}}'):
                                var_expr = part[2:-2].strip()
                                # print(f"DEBUG - Evaluating variable: {var_expr}")  # Debug
                            
                                if var_expr.startswith('='):
                                    # Handle eval expressions with enhanced calculation
                                    try:
                                        expr = var_expr[1:]
                                        result = self._evaluate_calculation(expr, loop_context)
                                        value = str(result)
                                    except Exception as e:
                                        value = f'[Error: {str(e)}]'
                                elif ' or ' in var_expr:
                                    # Handle 'or' operator for default values
                                    parts = var_expr.split(' or ')
                                    result = None
                                    for part_expr in parts:
                                        part_expr = part_expr.strip()
                                        # Remove quotes if it's a literal string
                                        if (part_expr.startswith('"') and part_expr.endswith('"')) or \
                                           (part_expr.startswith("'") and part_expr.endswith("'")):
                                            result = part_expr[1:-1]
                                            break
                                        else:
                                            # Evaluate the variable
                                            if '.' in part_expr:
                                                # Handle nested attribute access
                                                var_parts = part_expr.split('.')
                                                current = loop_context.get(var_parts[0], {})
                                                for var_part in var_parts[1:]:
                                                    if isinstance(current, dict):
                                                        current = current.get(var_part, '')
                                                    else:
                                                        current = getattr(current, var_part, '')
                                                    if current is None:
                                                        current = ''
                                                        break
                                                value = current
                                            else:
                                                # Simple variable access
                                                value = loop_context.get(part_expr, '')
                                            
                                            # If value is not empty or not zero, use it
                                            if value or value == 0:
                                                result = value
                                                break
                                    
                                    value = str(result if result is not None else '')
                                elif '.' in var_expr:
                                    # Handle nested attributes
                                    parts = var_expr.split('.')
                                    current = loop_context.get(parts[0], {})
                                    for part_name in parts[1:]:
                                        if isinstance(current, dict):
                                            current = current.get(part_name, '')
                                        else:
                                            current = getattr(current, part_name, '')
                                        if current is None:
                                            current = ''
                                            break
                                    value = str(current)
                                else:
                                    # Handle simple variable
                                    value = str(loop_context.get(var_expr, ''))
                            
                                # print(f"DEBUG - Variable value: {value}")  # Debug
                                item_output.append(value)
                                j += 1
                            
                            else:
                                # Handle literal text (preserve whitespace and newlines)
                                item_output.append(str(part))
                                j += 1
                        
                        rendered_item = ''.join(item_output)
                        # print(f"DEBUG - Rendered item {item_idx}:\n{repr(rendered_item)}")  # Debug
                        loop_output.append(rendered_item)
                    
                    if loop_output:
                        # Join all loop items with newlines and add to output
                        loop_result = '\n'.join(loop_output)
                        output.append(loop_result)
                    else:
                        # print("DEBUG - No loop output generated")
                        pass
                    
                    # Skip to end of loop
                    i = endfor_idx + 1
                    
                # Handle endif/endfor
                elif block in ('endif', 'endfor'):
                    i += 1
                    
                else:
                    i += 1
                    
            # Static text
            else:
                output.append(str(part) if part else '')
                i += 1
                
        # Clean up the output by removing excessive newlines
        result = ''.join(output)
        return self._clean_output(result)
    
    def _get_safe_globals(self) -> Dict[str, Any]:
        """Return a dictionary of safe builtins for eval/exec."""
        # 字符串操作函数
        def safe_upper(s):
            return str(s).upper() if s else ""
        
        def safe_lower(s):
            return str(s).lower() if s else ""
        
        def safe_title(s):
            return str(s).title() if s else ""
        
        def safe_capitalize(s):
            return str(s).capitalize() if s else ""
        
        def safe_strip(s):
            return str(s).strip() if s else ""
        
        def safe_lstrip(s):
            return str(s).lstrip() if s else ""
        
        def safe_rstrip(s):
            return str(s).rstrip() if s else ""
        
        def safe_split(s, sep=None, maxsplit=-1):
            return str(s).split(sep, maxsplit) if s else []
        
        def safe_join(sep, iterable):
            try:
                return str(sep).join(str(item) for item in iterable)
            except:
                return ""
        
        def safe_replace(s, old, new):
            return str(s).replace(str(old), str(new)) if s else ""
        
        def safe_startswith(s, prefix):
            return str(s).startswith(str(prefix)) if s else False
        
        def safe_endswith(s, suffix):
            return str(s).endswith(str(suffix)) if s else False
        
        def safe_contains(s, sub):
            return str(sub) in str(s) if s else False
        
        def safe_length(s):
            try:
                return len(s) if s is not None else 0
            except:
                return 0
        
        def safe_slice(s, start, end=None):
            try:
                if end is None:
                    return str(s)[start:]
                return str(s)[start:end]
            except:
                return "" if s else ""
        
        # 列表/数组操作函数
        def safe_first(iterable):
            try:
                return iterable[0] if iterable else None
            except:
                return None
        
        def safe_last(iterable):
            try:
                return iterable[-1] if iterable else None
            except:
                return None
        
        def safe_rest(iterable):
            try:
                return iterable[1:] if iterable else []
            except:
                return []
        
        def safe_take(iterable, n):
            try:
                return iterable[:n] if iterable else []
            except:
                return []
        
        def safe_reverse(iterable):
            try:
                return list(reversed(iterable)) if iterable else []
            except:
                return []
        
        def safe_sort(iterable, key=None, reverse=False):
            try:
                return sorted(iterable, key=key, reverse=reverse) if iterable else []
            except:
                return []
        
        def safe_unique(iterable):
            try:
                return list(dict.fromkeys(iterable)) if iterable else []
            except:
                return []
        
        def safe_concat(*lists):
            try:
                result = []
                for lst in lists:
                    if lst:
                        result.extend(lst)
                return result
            except:
                return []
        
        # 类型转换和检查函数
        def safe_to_string(value):
            return str(value) if value is not None else ""
        
        def safe_to_int(value, default=0):
            try:
                return int(value)
            except:
                return default
        
        def safe_to_float(value, default=0.0):
            try:
                return float(value)
            except:
                return default
        
        def safe_to_list(value):
            if value is None:
                return []
            elif isinstance(value, (list, tuple)):
                return list(value)
            elif isinstance(value, dict):
                return list(value.values())
            else:
                return [value]
        
        def safe_is_empty(value):
            if value is None:
                return True
            elif isinstance(value, (list, tuple, dict, str)):
                return len(value) == 0
            else:
                return False
        
        def safe_is_not_empty(value):
            return not safe_is_empty(value)
        
        def safe_is_numeric(value):
            try:
                float(value)
                return True
            except:
                return False
        
        def safe_type_of(value):
            return type(value).__name__
        
        # 数学扩展函数
        def safe_mean(iterable):
            try:
                if not iterable:
                    return 0
                return sum(iterable) / len(iterable)
            except:
                return 0
        
        def safe_median(iterable):
            try:
                if not iterable:
                    return 0
                sorted_list = sorted(iterable)
                n = len(sorted_list)
                if n % 2 == 0:
                    return (sorted_list[n//2-1] + sorted_list[n//2]) / 2
                else:
                    return sorted_list[n//2]
            except:
                return 0
        
        def safe_range(start, stop=None, step=1):
            try:
                if stop is None:
                    return list(range(start))
                return list(range(start, stop, step))
            except:
                return []
        
        # 日期时间函数
        def safe_now(format="%Y-%m-%d %H:%M:%S"):
            try:
                from datetime import datetime
                return datetime.now().strftime(format)
            except:
                return ""
        
        def safe_today(format="%Y-%m-%d"):
            try:
                from datetime import datetime
                return datetime.now().strftime(format)
            except:
                return ""
        
        def safe_year():
            try:
                from datetime import datetime
                return datetime.now().year
            except:
                return 0
        
        def safe_month():
            try:
                from datetime import datetime
                return datetime.now().month
            except:
                return 0
        
        def safe_day():
            try:
                from datetime import datetime
                return datetime.now().day
            except:
                return 0
        
        # 条件和逻辑函数
        def safe_coalesce(*args):
            for arg in args:
                if arg is not None and arg != "":
                    return arg
            return None
        
        def safe_default(value, default_value):
            return value if value is not None and value != "" else default_value
        
        def safe_conditional(condition, true_value, false_value):
            return true_value if condition else false_value
        
        # 局部变量操作函数
        def safe_set_var(name, value):
            """设置局部变量 - 这个函数会通过上下文管理器处理"""
            return value
        
        def safe_let(var_name, value):
            """let语法支持 - 创建临时变量绑定"""
            return value
        
        # URL和编码函数
        def safe_quote(s):
            try:
                import urllib.parse
                return urllib.parse.quote(str(s))
            except:
                return str(s)
        
        def safe_unquote(s):
            try:
                import urllib.parse
                return urllib.parse.unquote(str(s))
            except:
                return str(s)
        
        def safe_json_encode(value):
            try:
                import json
                return json.dumps(value, ensure_ascii=False)
            except:
                return ""
        
        def safe_json_decode(s):
            try:
                import json
                return json.loads(str(s))
            except:
                return None
        
        safe_builtins = {
            # 基础常量
            'None': None,
            'True': True,
            'False': False,
            # 基础类型
            'bool': bool,
            'int': int,
            'float': float,
            'str': str,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            # 基础函数
            'len': len,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'pow': pow,
            # 字符串操作
            'upper': safe_upper,
            'lower': safe_lower,
            'title': safe_title,
            'capitalize': safe_capitalize,
            'strip': safe_strip,
            'lstrip': safe_lstrip,
            'rstrip': safe_rstrip,
            'split': safe_split,
            'join': safe_join,
            'replace': safe_replace,
            'startswith': safe_startswith,
            'endswith': safe_endswith,
            'contains': safe_contains,
            'length': safe_length,
            'slice': safe_slice,
            # 列表/数组操作
            'first': safe_first,
            'last': safe_last,
            'rest': safe_rest,
            'take': safe_take,
            'reverse': safe_reverse,
            'sort': safe_sort,
            'unique': safe_unique,
            'concat': safe_concat,
            # 类型转换和检查
            'to_string': safe_to_string,
            'to_int': safe_to_int,
            'to_float': safe_to_float,
            'to_list': safe_to_list,
            'is_empty': safe_is_empty,
            'is_not_empty': safe_is_not_empty,
            'is_numeric': safe_is_numeric,
            'type_of': safe_type_of,
            # 数学函数
            'sqrt': lambda x: x ** 0.5,
            'ceil': lambda x: int(x) + (1 if x > int(x) else 0),
            'floor': int,
            'mean': safe_mean,
            'median': safe_median,
            'range': safe_range,
            # 日期时间
            'now': safe_now,
            'today': safe_today,
            'year': safe_year,
            'month': safe_month,
            'day': safe_day,
            # 逻辑和条件
            'coalesce': safe_coalesce,
            'default': safe_default,
            'conditional': safe_conditional,
            # 局部变量操作
            'set': safe_set_var,
            'let': safe_let,
            # URL和编码
            'quote': safe_quote,
            'unquote': safe_unquote,
            'json_encode': safe_json_encode,
            'json_decode': safe_json_decode,
        }
        return safe_builtins

    def _is_safe_expression(self, expr: str) -> bool:
        """Check if an expression contains potentially dangerous operations."""
        forbidden = [
            'import', 'open', 'exec', 'eval', 'system', 'subprocess',
            '__import__', 'getattr', 'setattr', 'delattr', 'compile',
            'globals', 'locals', 'vars', 'dir', 'help', 'reload',
            'input', 'file', 'execfile', 'reload', 'exit', 'quit'
        ]
        expr_lower = expr.lower()
        return not any(keyword in expr_lower for keyword in forbidden)

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> tuple:
        """
        Evaluate a condition expression or code block in the given context.
        Returns (result, updated_context) where updated_context contains any new variables
        created during evaluation.
        """
        try:
            if not self._is_safe_expression(condition):
                raise ValueError(f"Potentially dangerous expression: {condition}")
                
            # Special handling for loop variables
            if 'loop.' in condition:
                # Handle not conditions
                has_not = 'not ' in condition
                loop_var = condition.split('loop.')[-1].strip()
                if has_not:
                    loop_var = loop_var.replace('not ', '').strip()
                
                loop_info = context.get('loop', {})
                result = False
                
                if loop_var == 'last':
                    result = loop_info.get('last', False)
                elif loop_var == 'first':
                    result = loop_info.get('first', False)
                elif loop_var == 'index':
                    result = bool(loop_info.get('index', 0))
                elif loop_var == 'index0':
                    result = bool(loop_info.get('index0', 0))
                
                # Invert result if 'not' was present
                return (not result if has_not else result), context
                    
            # Create safe evaluation environment
            safe_globals = self._get_safe_globals()
            eval_globals = {**safe_globals, **self.custom_functions}
            
            # Make a copy of context to avoid modifying the original
            local_vars = context.copy()
            
            # Handle multi-line code blocks
            if '\n' in condition.strip():
                # Compile and execute the code block in restricted environment
                code = compile(condition, '<string>', 'exec')
                exec(code, eval_globals, local_vars)
                # The last expression's value should be in __result__
                result = bool(local_vars.get('__result__', False))
                # Return result and updated context (excluding special vars)
                updated_context = {k: v for k, v in local_vars.items() 
                                 if not k.startswith('__') and k not in self.custom_functions}
                
                # Debug output
                print(f"DEBUG - Condition evaluation result: {result}")
                print(f"DEBUG - Local vars after execution: {local_vars.keys()}")
                print(f"DEBUG - Updated context to return: {updated_context.keys()}")
                
                # Ensure all calculated variables are included
                for k, v in local_vars.items():
                    if (not k.startswith('__') and 
                        k not in self.custom_functions and 
                        k not in updated_context):
                        updated_context[k] = v
                
                return result, updated_context
            
            # Handle function calls with = prefix
            if condition.startswith('='):
                result = bool(eval(condition[1:], eval_globals, local_vars))
                return result, local_vars
            
            # Handle nested attribute access (e.g. user.is_admin)
            if '.' in condition:
                parts = condition.split('.')
                current = local_vars.get(parts[0], {})
                for part in parts[1:]:
                    if isinstance(current, dict):
                        current = current.get(part, None)
                    else:
                        current = getattr(current, part, None)
                    if current is None:
                        return False, local_vars
                # Handle empty collections
                if isinstance(current, (list, dict, set)) and not current:
                    return False, local_vars
                return bool(current), local_vars
            
            # Handle direct variable reference
            if condition in local_vars:
                value = local_vars[condition]
                if isinstance(value, (list, dict, set)):
                    return len(value) > 0, local_vars
                return bool(value), local_vars
                
            # Evaluate other expressions
            result = bool(eval(condition, eval_globals, local_vars))
            return result, local_vars
            
        except Exception:
            return False, context
            
    def _skip_control_block(self, start_idx: int, start_tag: str, end_tag: str) -> int:
        """Skip a control block until matching end tag is found."""
        if start_idx >= len(self.compiled):
            return len(self.compiled)
            
        depth = 1
        i = start_idx + 1
        # print(f"DEBUG - Searching for {end_tag} starting from {start_idx}")
        
        while i < len(self.compiled):
            part = self.compiled[i]
            if isinstance(part, str) and part.startswith('{%') and part.endswith('%}'):
                block = part[2:-2].strip()
                # print(f"DEBUG - Token {i}: {block} (depth={depth})")
                
                # Handle nested blocks
                if block.startswith('if ') or block.startswith('for '):
                    depth += 1
                    # print(f"DEBUG - Found nested block, depth increased to {depth}")
                elif block == end_tag:
                    depth -= 1
                    # print(f"DEBUG - Found {end_tag}, depth decreased to {depth}")
                    if depth == 0:
                        # print(f"DEBUG - Found matching {end_tag} at {i}")
                        return i
                elif block == 'else' and depth == 1:
                    # print(f"DEBUG - Found else at {i}")
                    # Don't decrease depth for else blocks
                    pass
                elif block in ['endif', 'endfor'] and depth > 1:
                    depth -= 1
                    # print(f"DEBUG - Found closing tag in nested block, depth decreased to {depth}")
            
            i += 1
        
        # print(f"DEBUG - Error: Reached end without finding matching {end_tag} (current depth: {depth})")
        # print(f"DEBUG - Last processed block: {self.compiled[i-1] if i > 0 else 'None'}")
        return len(self.compiled)

    def _clean_output(self, output: str) -> str:
        """Clean up the final output while preserving essential formatting."""
        output = re.sub(r"\n+", "\n", output)     
        lines = output.split('\n')
        cleaned = []
        
        for line in lines:
            # Preserve all lines including empty ones that are part of the template structure
            cleaned.append(line)
        # Join lines while preserving original newlines and indentation
        return '\n'.join(cleaned) 
        
    def _parse_for_block(self, block: str) -> tuple:
        """Parse a for block into loop variable and iterable parts."""
        parts = block[4:].split(' in ', 1)
        return parts[0].strip(), parts[1].strip()
        
    def _get_iterable(self, iterable: str, context: Dict[str, Any]) -> List[Any]:
        """Get an iterable from context or evaluate expression."""
        if iterable in context:
            return context[iterable]
        try:
            if not self._is_safe_expression(iterable):
                raise ValueError("Potentially dangerous expression detected")
            
            safe_globals = self._get_safe_globals()
            return eval(iterable, safe_globals, context)
        except Exception:
            return []
            
    def _process_includes(self, template: str) -> str:
        """Process {% include 'filename' %} directives."""
        include_pattern = re.compile(r'\{\%\s*include\s+[\'"]([^\'"]+)[\'"]\s*\%\}')
        
        def replace_include(match):
            filename = match.group(1)
            content = self._load_include_file(filename)
            return content
        
        # Recursively process includes
        while include_pattern.search(template):
            template = include_pattern.sub(replace_include, template)
        
        return template
    
    def _load_include_file(self, filename: str) -> str:
        """Load content from an included template file."""
        if self.template_dir:
            file_path = os.path.join(self.template_dir, filename)
        else:
            file_path = filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Recursively process includes in the included file
            included_parser = TemplateParser(content, self.template_dir)
            return included_parser._process_includes(content)
        except FileNotFoundError:
            return f"[Error: Include file '{filename}' not found]"
        except Exception as e:
            return f"[Error: Failed to include '{filename}': {str(e)}]"
    
    def _evaluate_calculation(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate mathematical expressions with enhanced safety and local variable support."""
        if not self._is_safe_expression(expr):
            raise ValueError(f"Potentially dangerous expression: {expr}")
        
        # Check for set/let expressions
        stripped_expr = expr.strip()
        
        # Handle set variable: set('var_name', value)
        if stripped_expr.startswith('set('):
            try:
                # Parse set('var_name', value)
                import re
                match = re.match(r"set\(['\"]([^'\"]+)['\"]\s*,\s*(.+)\)", stripped_expr)
                if match:
                    var_name = match.group(1)
                    value_expr = match.group(2)
                    
                    # Evaluate the value
                    safe_globals = self._get_safe_globals()
                    safe_globals.update({
                        'pow': pow,
                        'sqrt': lambda x: x ** 0.5,
                        'ceil': lambda x: int(x) + (1 if x > int(x) else 0),
                        'floor': int,
                        'abs': abs,
                        'round': round,
                        'min': min,
                        'max': max,
                        'sum': sum
                    })
                    eval_globals = {**safe_globals, **self.custom_functions}
                    
                    value = eval(value_expr, eval_globals, context)
                    
                    # Store in context for future use
                    context[var_name] = value
                    
                    return value
            except Exception as e:
                return f"[Set Error: {str(e)}]"
        
        # Handle let expression: let('var_name', value)
        elif stripped_expr.startswith('let('):
            try:
                # Parse let('var_name', value)
                import re
                match = re.match(r"let\(['\"]([^'\"]+)['\"]\s*,\s*(.+)\)", stripped_expr)
                if match:
                    var_name = match.group(1)
                    value_expr = match.group(2)
                    
                    # Evaluate the value
                    safe_globals = self._get_safe_globals()
                    safe_globals.update({
                        'pow': pow,
                        'sqrt': lambda x: x ** 0.5,
                        'ceil': lambda x: int(x) + (1 if x > int(x) else 0),
                        'floor': int,
                        'abs': abs,
                        'round': round,
                        'min': min,
                        'max': max,
                        'sum': sum
                    })
                    eval_globals = {**safe_globals, **self.custom_functions}
                    
                    value = eval(value_expr, eval_globals, context)
                    
                    # Create a new context with the local variable
                    # In let expressions, the variable is available within the current evaluation scope
                    context[var_name] = value
                    
                    return value
            except Exception as e:
                return f"[Let Error: {str(e)}]"
        
        # Enhanced safe globals with math functions
        safe_globals = self._get_safe_globals()
        safe_globals.update({
            'pow': pow,
            'sqrt': lambda x: x ** 0.5,
            'ceil': lambda x: int(x) + (1 if x > int(x) else 0),
            'floor': int,
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum
        })
        
        eval_globals = {**safe_globals, **self.custom_functions}
        
        try:
            return eval(expr, eval_globals, context)
        except Exception as e:
            return f"[Calculation Error: {str(e)}]"

    def _render_parts(self, parts: List[Union[str, None]], context: Dict[str, Any]) -> str:
        """Render a list of template parts with the given context."""
        temp_parser = TemplateParser('', self.template_dir)
        temp_parser.compiled = parts
        
        # Create a copy of context for this rendering scope
        local_context = context.copy()
        
        # Process parts to handle set/let statements
        processed_parts = []
        i = 0
        while i < len(parts):
            part = parts[i]
            
            if (isinstance(part, str) and 
                part.startswith('{%') and 
                part.endswith('%}')):
                block = part[2:-2].strip()
                
                # Handle set variable
                if block.startswith('set '):
                    set_content = block[4:].strip()
                    if '=' in set_content:
                        var_name, value_expr = set_content.split('=', 1)
                        var_name = var_name.strip()
                        value_expr = value_expr.strip()
                        
                        # Evaluate value expression
                        try:
                            if value_expr.startswith('='):
                                value_expr = value_expr[1:]
                            value = self._evaluate_calculation(value_expr, local_context)
                            # Store in local context
                            local_context[var_name] = value
                        except Exception as e:
                            local_context[var_name] = f"[Set Error: {str(e)}]"
                    
                    # Skip this part (set statement doesn't produce output)
                    i += 1
                    continue
                
                # Handle let variable  
                elif block.startswith('let '):
                    let_content = block[4:].strip()
                    if '=' in let_content:
                        var_name, value_expr = let_content.split('=', 1)
                        var_name = var_name.strip()
                        value_expr = value_expr.strip()
                        
                        # Evaluate value expression
                        try:
                            if value_expr.startswith('='):
                                value_expr = value_expr[1:]
                            value = self._evaluate_calculation(value_expr, local_context)
                            # Store in local context
                            local_context[var_name] = value
                        except Exception as e:
                            local_context[var_name] = f"[Let Error: {str(e)}]"
                    
                    # Skip this part (let statement doesn't produce output)
                    i += 1
                    continue
            
            processed_parts.append(part)
            i += 1
        
        temp_parser.compiled = processed_parts
        return temp_parser.render(local_context)


# Example usage
if __name__ == '__main__':
    template = """
    <html>
    <body>
        <h1>Hello {{ name }}!</h1>
        
        {% if show_details %}
        <div class="details">
            <p>Your details:</p>
            <ul>
                {% for item in items %}
                <li>{{ item }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
    </body>
    </html>
    """
    
    context = {
        'name': 'World',
        'show_details': True,
        'items': ['Item 1', 'Item 2', 'Item 3']
    }
    
    parser = TemplateParser(template)
    result = parser.render(context)
    print(result)
    
    # 示例代码 - 自定义函数功能
    print("\n=== 自定义函数示例 ===")
    
    # 创建使用自定义函数的模板
    func_template = """
    {{= greet(name) }}
    {{= calculate(10, 20) }}
    {{= format_date(now) }}
    
    {% if 
        # 多行代码块示例
        user = context.get('user')
        premium = user.get('membership') == 'premium'
        active = user.get('is_active', False)
        __result__ = premium and active
    %}
    <p>Welcome premium user {{ user.name }}!</p>
    {% else %}
    <p>Welcome standard user {{ user.name }}!</p>
    {% endif %}
    
    {% if 
        # 带计算的代码块示例
        total = calculate(10, 20)
        discount = 0.2 if user.get('membership') == 'premium' else 0.1
        final_price = total * (1 - discount)
        __result__ = final_price > 15
    %}
    <p>Special discount applied! Final price: {{ final_price }}</p>
    {% endif %}
    """
    
    # Include 和数学计算示例
    print("\n=== Include 和数学计算示例 ===")
    
    # 创建示例模板文件
    os.makedirs('templates', exist_ok=True)
    with open('templates/header.html', 'w', encoding='utf-8') as f:
        f.write("""<header>
    <h1>{{ site_title }}</h1>
    <nav>
        <a href="/">首页</a> | 
        <a href="/about">关于</a>
    </nav>
</header>""")
    
    with open('templates/footer.html', 'w', encoding='utf-8') as f:
        f.write("""<footer>
    <p>&copy; {{ year }} {{ company_name }}</p>
    <p>页面生成时间: {{= current_time() }}</p>
</footer>""")
    
    # 使用 include 和数学计算的模板
    include_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ page_title }}</title>
    </head>
    <body>
        {% include 'header.html' %}
        
        <main>
            <h2>{{ page_title }}</h2>
            
            <h3>数学计算示例:</h3>
            <ul>
                <li>基础运算: {{= 10 + 5 * 2 }}</li>
                <li>幂运算: {{= pow(2, 8) }}</li>
                <li>平方根: {{= sqrt(16) }}</li>
                <li>向上取整: {{= ceil(3.2) }}</li>
                <li>向下取整: {{= floor(3.8) }}</li>
                <li>绝对值: {{= abs(-5) }}</li>
                <li>四舍五入: {{= round(3.14159, 2) }}</li>
            </ul>
            
            <h3>复杂计算:</h3>
            <p>圆的面积 (半径=5): {{= 3.14159 * pow(5, 2) }}</p>
            <p>商品价格计算: 
                原价: {{ price }}元, 
                折扣: {{ discount }}%, 
                最终价格: {{= price * (1 - discount/100) }}元
            </p>
            
            <h3>条件计算:</h3>
            {% if score >= 90 %}
                <p>优秀成绩: {{ score }}分</p>
            {% elif score >= 60 %}
                <p>及格成绩: {{ score }}分</p>
            {% else %}
                <p>需要努力: {{ score }}分</p>
            {% endif %}
        </main>
        
        {% include 'footer.html' %}
    </body>
    </html>
    """
    
    # 定义自定义函数
    def greet(name):
        return f"Hello, {name}!"
        
    def calculate(x, y):
        return x + y
        
    def format_date(dt):
        return dt.strftime("%Y-%m-%d")
        
    def is_premium_user(user):
        return user.get('membership') == 'premium'
    
    def current_time():
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 创建解析器并注册函数
    func_parser = TemplateParser(func_template)
    func_parser.register_function('greet', greet)
    func_parser.register_function('calculate', calculate)
    func_parser.register_function('format_date', format_date)
    func_parser.register_function('is_premium_user', is_premium_user)
    
    # 准备上下文
    from datetime import datetime
    func_context = {
        'name': 'Function User',
        'now': datetime.now(),
        'user': {
            'name': 'test_user',
            'membership': 'premium'  # 测试 premium 用户
        }
    }
    
    # 渲染并打印结果
    func_result = func_parser.render(func_context)
    print(func_result)
    
    # 创建带模板目录的解析器用于 include 功能
    include_parser = TemplateParser(include_template, template_dir='templates')
    include_parser.register_function('current_time', current_time)
    
    include_context = {
        'page_title': 'Include 和数学计算演示',
        'site_title': '我的网站',
        'year': '2024',
        'company_name': '示例公司',
        'price': 100,
        'discount': 20,
        'score': 85
    }
    
    include_result = include_parser.render(include_context)
    print("\n=== Include 模板渲染结果 ===")
    print(include_result)
    
    # 新增变量操作函数示例
    print("\n=== 变量操作函数示例 ===")
    
    # 创建包含各种变量操作的模板
    var_ops_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>变量操作函数演示</title>
    </head>
    <body>
        <h1>字符串操作</h1>
        <ul>
            <li>转大写: {{= upper(text) }}</li>
            <li>转小写: {{= lower(text) }}</li>
            <li>标题格式: {{= title(text) }}</li>
            <li>首字母大写: {{= capitalize(text) }}</li>
            <li>去除空格: '{{= strip(whitespace_text) }}'</li>
            <li>分割成数组: {{= split(csv_text, ',') }}</li>
            <li>替换文本: {{= replace(text, 'World', 'Template') }}</li>
            <li>字符串长度: {{= length(text) }}</li>
            <li>包含检查: {{= contains(text, 'Hello') }}</li>
            <li>切片操作: {{= slice(text, 0, 5) }}</li>
        </ul>
        
        <h1>列表操作</h1>
        <ul>
            <li>第一个元素: {{= first(items) }}</li>
            <li>最后一个元素: {{= last(items) }}</li>
            <li>除第一个外的元素: {{= rest(items) }}</li>
            <li>取前3个元素: {{= take(items, 3) }}</li>
            <li>反转列表: {{= reverse(items) }}</li>
            <li>排序列表: {{= sort(unsorted_items) }}</li>
            <li>去重列表: {{= unique(duplicate_items) }}</li>
            <li>列表连接: {{= concat(items, more_items) }}</li>
        </ul>
        
        <h1>类型转换</h1>
        <ul>
            <li>转字符串: {{= to_string(number) }}</li>
            <li>转整数: {{= to_int(decimal_num) }}</li>
            <li>转浮点数: {{= to_float(int_num) }}</li>
            <li>转列表: {{= to_list(single_value) }}</li>
            <li>是否为空: {{= is_empty(empty_var) }}</li>
            <li>是否不为空: {{= is_not_empty(text) }}</li>
            <li>是否为数字: {{= is_numeric(number) }}</li>
            <li>变量类型: {{= type_of(items) }}</li>
        </ul>
        
        <h1>数学计算</h1>
        <ul>
            <li>平均值: {{= mean(numbers) }}</li>
            <li>中位数: {{= median(numbers) }}</li>
            <li>范围数组: {{= range(1, 6) }}</li>
            <li>平方根: {{= sqrt(16) }}</li>
            <li>向上取整: {{= ceil(3.2) }}</li>
            <li>向下取整: {{= floor(3.8) }}</li>
        </ul>
        
        <h1>日期时间</h1>
        <ul>
            <li>当前时间: {{= now() }}</li>
            <li>今天日期: {{= today() }}</li>
            <li>当前年份: {{= year() }}</li>
            <li>当前月份: {{= month() }}</li>
            <li>当前日期: {{= day() }}</li>
        </ul>
        
        <h1>逻辑和条件</h1>
        <ul>
            <li>合并非空值: {{= coalesce(null_var, empty_var, text, 'default') }}</li>
            <li>默认值: {{= default(null_var, 'Default Value') }}</li>
            <li>条件选择: {{= conditional(score > 80, '优秀', '一般') }}</li>
        </ul>
        
        <h1>URL和编码</h1>
        <ul>
            <li>URL编码: {{= quote(text_with_spaces) }}</li>
            <li>URL解码: {{= unquote(encoded_text) }}</li>
            <li>JSON编码: {{= json_encode(data_obj) }}</li>
            <li>JSON解码: {{= json_decode(json_str).name }}</li>
        </ul>
        
        <h1>循环中使用函数</h1>
        {% for item in mixed_items %}
            <p>
                索引 {{ loop.index }}: {{= upper(to_string(item)) }}
                {% if is_numeric(item) %}
                    (数字，平方根: {{= sqrt(item) }})
                {% else %}
                    (字符串，长度: {{= length(item) }})
                {% endif %}
            </p>
        {% endfor %}
    </body>
    </html>
    """
    
    # 创建解析器并渲染
    var_parser = TemplateParser(var_ops_template)
    var_context = {
        'text': 'Hello World',
        'whitespace_text': '  Hello World  ',
        'csv_text': 'apple,banana,cherry',
        'items': ['apple', 'banana', 'cherry'],
        'more_items': ['date', 'elderberry'],
        'unsorted_items': [3, 1, 4, 1, 5, 9],
        'duplicate_items': [1, 2, 2, 3, 3, 4],
        'number': 42,
        'decimal_num': '3.14',
        'int_num': 42,
        'single_value': 'single',
        'empty_var': '',
        'null_var': None,
        'numbers': [1, 2, 3, 4, 5],
        'score': 85,
        'text_with_spaces': 'hello world',
        'encoded_text': 'hello%20world',
        'data_obj': {'name': 'test', 'value': 100},
        'json_str': '{"name": "JSON", "value": 200}',
        'mixed_items': ['hello', 16, 'world', 25, 'python', 36]
    }
    
    var_result = var_parser.render(var_context)
    print(var_result)
    
    # 局部变量示例
    print("\n=== 局部变量示例 ===")
    
    # 创建包含局部变量操作的模板
    local_var_template = """
    <h1>局部变量演示</h1>
    
    <h2>使用 set 语句设置变量</h2>
    {% set greeting = "Hello" %}
    {% set user_name = "Alice" %}
    {% set user_age = 25 %}
    <p>{{ greeting }}, {{ user_name }}! You are {{ user_age }} years old.</p>
    
    <h2>使用 let 语句创建临时变量</h2>
    {% let temp_result = 100 * 1.2 %}
    <p>临时计算结果: {{ temp_result }}</p>
    
    <h2>在条件语句中使用局部变量</h2>
    {% set discount_rate = 0.2 %}
    {% set original_price = 200 %}
    {% set final_price = original_price * (1 - discount_rate) %}
    
    {% if final_price < 150 %}
        <p>折扣后价格: {{ final_price }} - 优惠价格!</p>
    {% else %}
        <p>折扣后价格: {{ final_price }}</p>
    {% endif %}
    
    <h2>在循环中使用局部变量</h2>
    {% set prefix = "Item" %}
    {% for item in [10, 20, 30, 40] %}
        {% set doubled = item * 2 %}
        {% let is_even = (item % 2 == 0) %}
        <p>{{ prefix }} {{ loop.index }}: Original = {{ item }}, Doubled = {{ doubled }}, Is Even = {{ is_even }}</p>
    {% endfor %}
    
    <h2>复杂的变量操作</h2>
    {% let base_text = "Template Engine" %}
    {% set processed_text = upper(base_text) %}
    {% set text_length = length(processed_text) %}
    {% set reversed_text = reverse(list(processed_text)) %}
    <p>原始文本: {{ base_text }}</p>
    <p>处理后: {{ processed_text }}</p>
    <p>长度: {{ text_length }}</p>
    <p>反转字符列表: {{ reversed_text }}</p>
    
    <h2>函数调用中的局部变量</h2>
    {% set current_time = now("%H:%M:%S") %}
    {% set greeting_msg = conditional(length(current_time) > 10, "时间详细", "时间简洁") %}
    <p>当前时间: {{ current_time }} ({{ greeting_msg }})</p>
    
    <h2>嵌套的局部变量</h2>
    {% set outer_var = "Outer" %}
    {% if True %}
        {% let inner_var = "Inner" %}
        {% set combined = outer_var + " " + inner_var %}
        <p>组合结果: {{ combined }}</p>
    {% endif %}
    <p>外部变量仍然存在: {{ outer_var }}</p>
    """
    
    # 创建解析器并渲染
    local_parser = TemplateParser(local_var_template)
    local_result = local_parser.render({
        'user_info': {
            'name': 'Test User',
            'email': 'test@example.com'
        }
    })
    print(local_result)
    
    # 清理创建的示例文件
    import shutil
    if os.path.exists('templates'):
        shutil.rmtree('templates')