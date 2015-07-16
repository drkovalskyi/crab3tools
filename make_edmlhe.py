#!/bin/env python
import sys,re,commands,os,shutil,pprint,subprocess
from optparse import OptionParser

description = """
Convert XML-based LHE files into EDM file format. The tool requires
CMSSW environment and uses cmsRun to perform the conversion.
"""
parser = OptionParser(usage = "\n\t%prog [options]", description = description)
parser.add_option("-f", "--lhe", dest="lhe", help="LHE file (LFN or PFN)",
                  metavar="FILE")
parser.add_option("-d", "--dir", dest="dir", metavar="PATH",
                  help="PATH containing LHE files (LFN or PFN)")
parser.add_option("-l", "--lumi", dest="lumi", metavar="NUMBER", default=100,
                  help="Events per luminosity block [default: %default]")
parser.add_option("-c", "--cfg", dest="config", metavar="FILE", default="lhe2edmlhe_cfg.py",
                  help="cmsRun config file [default: %default]")
parser.add_option("-o", "--output", dest="output", metavar="FILE",
                  help="Output EDM file name. If not provided it's generated from LHE file/directory name")

(options, args) = parser.parse_args()

if not options.lhe and not options.dir:
    parser.print_help()
    sys.exit()
if not 'CMSSW_VERSION' in os.environ:
    raise Exception('CMSSW enviroment is required')

# ==========================================================================

def get_xrootd_link(lfn):
    return "root://cms-xrd-global.cern.ch/%s"%lfn

def is_lfn(link):
    if re.search(r'^/store/',link):
        return True
    return False

def cleanup_text(text):
    while text != re.sub('\([^\(]*?\)','',text):
        text = re.sub('\([^\(]*?\)','',text)
    return text

inputFiles = []
outputFile = None

# handle single file case first
if options.lhe:
    if is_lfn(options.lhe):
        inputFiles.append(get_xrootd_link(options.lhe))
    else:
        # check if PFN is accessible
        if not os.path.exists(options.lhe):
            raise Exception("PFN %s doesn't exist"%options.lhe)
        inputFiles.append("file:%s" % options.lhe)
    match = re.search('^[^\/].*?([^\/]+).lhe',options.lhe)
    if match:
        outputFile = "%s.root" % match.group(1) 

# handle directory case
eospath = sys.argv[2]
if options.dir:
    is_lfn = False
    # get file names in the directory
    command = "find %s -maxdepth 1 -type f" % options.dir
    if re.search('^/store/',options.dir):
        command = "xrdfs eoscms ls %s" % options.dir
        is_lfn = True
    (status,output) = commands.getstatusoutput(command)
    if status!=0:
        raise Exception("Failed to list files in the input directory\n" + output)
    filenames = output.split("\n")
    for file in filenames:
        # print file
        if is_lfn:
            inputFiles.append(get_xrootd_link(file))
        else:
            inputFiles.append("file:%s"%file)
    # use last directory name part as taskname
    match = re.search('([^\/]+)(\/*)$',options.dir)
    if match:
        outputFile = "%s.root" % match.group(1)

if options.output:
    outputFile = options.output

print "Input files:"
pprint.pprint(inputFiles)
print outputFile

tmp_config = subprocess.check_output(['mktemp']).strip("\n")+"_cfg.py"
print tmp_config
setOutput = False
with open(options.config,'r') as fIn:
    with open(tmp_config,'w') as fOut:
        inputBlock = None
        for line in fIn:
            if re.search('file:edmlhe.root',line):
                line = re.sub('file:edmlhe.root','file:%s'%outputFile,line)
                setOutput = True
            if re.search('LHESource',line):
                inputBlock = cleanup_text(line)
            elif inputBlock:
                inputBlock = cleanup_text(inputBlock + line)
            if inputBlock: 
                if not re.search('\(',inputBlock):
                    code = "\tfileNames = cms.untracked.vstring(\n"
                    for file in inputFiles:
                        code = code + ("\t\t'%s',\n" % file)
                    code = code + "\t),\n"
                    code = code + "\tnumberEventsInLuminosityBlock = cms.untracked.uint32(%d)\n" % options.lumi
                    inputBlock = re.sub('cms.Source','cms.Source("LHESource",\n%s\n)\n' % code,inputBlock)
                    fOut.write(inputBlock)
                    inputBlock = None
                continue
            fOut.write(line)

if not setOutput:
    raise Exception("Failed to set output file name properly")

command = "cmsRun %s" % tmp_config
exit_code = subprocess.call(command, shell=True)
