#!/usr/bin/python

import re
import sys
import os


srcStr = "LOGD"
targetStr = "VLOG(MIN_LOG_LEVEL)"

class converter:

  # Line contains printf, return a string containing the entire printf without newlines
  # Will read additional lines from f until reaching the end of the printf statement
  @staticmethod
  def _coalesce_printf(line, f):
    match = re.match(r'(.*)printf\((.*?)\);(.*)', line);
    if match is None:
      match = re.match(r'(.*)printf\((.*)', line);
      assert(match is not None)
      before = match.group(1)
      print_statement = match.group(2)
      for line in f:
        match = re.match(r'(.*?)\);(.*)', line)
        if match is None:
          match = re.match(r'(.*)', line)
          assert(match is not None)
          print_statement += match.group(1)
        else:
          print_statement += match.group(1)
          after = match.group(2)
          break
    else:
      before = match.group(1)
      print_statement = match.group(2)
      after = match.group(3)

    print_statement = re.sub(r'\"(\s*)\"', '', print_statement)

    return (print_statement, before, after)

  @staticmethod
  def _process_printf(line, f, prefix):
    (printf, before, after) = converter._coalesce_printf(line, f)
    mid = converter._printf_to_cout(prefix, printf)
    #format the multi-line print body
    format_mid = mid
    if  len(before) + len(mid) > 100:
      split3 = mid.split("<<")
      cnt = 1
      for ind, item in enumerate(split3):
        if ind == 0:
          format_mid = item
          continue
        if len(before) + len(format_mid) + len(item) > cnt * 100:
          format_mid += "\n" +  ' ' * (len(before) + len(prefix) + 1)    + "<<" + item
          cnt += 1
        else:
          format_mid += "<<" + item

    return before + format_mid + after

  @staticmethod
  def _process_fprintf(line, f):
    if 'stdout' in line:
      line = re.sub(r'fprintf\((\s*)stdout(\s*),\s*', 'printf(', line)
      prefix = 'std::cout'
    elif 'stderr' in line:
      line = re.sub(r'fprintf\((\s*)stderr(\s*),\s*', 'printf(', line)
      prefix = 'std::cerr'
    else:
      prefix = re.search(r'fprintf\((.*?),', line).group(1)
      line = re.sub(r'fprintf\(' + prefix + ',', 'printf(', line)
    return converter._process_printf(line, f, prefix)

  @staticmethod
  def _process_LOG(line, f):
    LOGStrs = ["LOGD", "LOGDLH", "XWJLOGD", "MAPLOGD", "VIOMAPLOGD",
              "FASTLOGD", "TESTLOGD", "LOOPLOGD", "PLANELOGD", 
              "SELFLOGD", "SOLVERLOGD", "ThreeDOFLOGD", 
              "VIOLOGD", "FELOGD", "WSLOGD", "CQLOGD", 
              "COUPLELOGD", "BACKLOGD"]
    for itemStr in LOGStrs:
      if re.search(r'(\s|^)' + itemStr + r'\(', line):
        line = re.sub(itemStr + r'\(', 'printf(', line)
        return converter._process_printf(line, f, targetStr)
    return line

  @staticmethod
  def _process_PRINT_(line, f):
    LOGStrs = ["PRINT_VAR", "PRINT_W", "PRINT_I", "PRINT_D", "PRINT_E"]
    for itemStr in LOGStrs:
      if re.search(r'(\s|^)' + itemStr + r'\(', line):
        line = re.sub(itemStr + r'\(', 'printf(', line)
        return converter._process_printf(line, f, targetStr)
    return line



  format_string = re.compile(r'(%\d*\.?\d*[hlLzjt]*[diufFeEgGxXoscpaAn])')
  @staticmethod
  def _printf_to_cout(prefix, line):
    result = prefix
    split = line.strip().split('",')
    string = split[0][1:] # remove first quotation mark with [1:]
    if len(split) > 1:
      args = split[1].split(',')
    else:
      args = []
      string = string[:-1] # remove last quotation mark
    split2 = converter.format_string.split(string)
    n_args = len(re.findall(converter.format_string, string))
    if n_args != len(args):
      print("\n\nERROR: mismatched arguments for line: " + line)
      print("Expected " + str(n_args) + " but provided " + str(len(args)))
      print(args)
      assert(False)
    current_arg = 0
    for string in split2:
      if re.match(converter.format_string, string):
        if 'x' in string:
          result += ' << std::hex'
        result += " << " + args[current_arg].strip()
        if 'x' in string:
          result += ' << std::dec'
        current_arg += 1
      else:
        result += ' << "' + string + '"'
    result += ';'
    result = re.sub(r'\\n', '" << std::endl << "', result)
    result = re.sub(r' << ""', '', result)
    result += "\n"
    return result
 
                                                         
  @staticmethod
  def _process_line(line, f):
    if re.search(r'(\s|^)\#define', line):
      return line
    if re.search(r'(\s|^)\/\/', line):
      return line
    if re.search(r'(\s|^)PRINT_.*\(', line):
      res = converter._process_PRINT_(line, f)
      print(res)
      return res
      # return converter._process_fprintf(line, f)
    elif re.search(r'(\s*.*)LOGD.*\(', line):
      tmp = converter._process_LOG(line, f)
      print(tmp)
      return tmp
    # elif re.search((r'(\s)' + 'printf' + r'\('), line):
      # return converter._process_printf(line, f, targetStr)
    else:
      return line

  @staticmethod
  def process_file(f):
    output = ''
    for line in f:
      output += converter._process_line(line, f)
    return output


if __name__ == '__main__':
  with open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin as f:
    res = (converter.process_file(f))
    # exit()
  for root,dirs,files in os.walk(r"/data/workspace/SenseVIO/example"):
    for file in files:
      # 获取文件所属目录
      # print(root)
      #获取文件路径
      targetFile =  os.path.join(root,file)
      print(targetFile)
      result = ""
      with open(targetFile) as f:
        result =  converter.process_file(f)
        # print(result)
      file = open(targetFile, mode="w")
      file.write(result)
      file.close


