#!/usr/bin/env python
# -*- coding: cp1252 -*-

""" SavReaderWriter.py: A Python interface to the IBM SPSS Statistics Input Output Module
(Linux: libspssdio.so.1, Mac: libspssdio.dylib, Windows: spssio32.dll). Read or Write SPSS system files (.sav) """

# NOW WORKS WITH LINUX (Tested with Linux Ubuntu 10) AND MAC OS (Thanks to Rich Sadowsky!)
# libspssdio.so.1, libspssdio.dylib, spssio32.dll + associated libaries and documentation can be downloaded here:
# https://www.ibm.com/developerworks/mydeveloperworks/wikis/home/wiki/We70df3195ec8_4f95_9773_42e448fa9029/page/Downloads%20for%20IBM%C2%AE%20SPSS%C2%AE%20Statistics?lang=en
# NOTE: This supersedes SavReader.py
# NOTE: Added SavDataDictionaryReader/Writer classes to read/write the Spss data file header
# ANY FEEDBACK ON THIS CODE IS WELCOME: "@".join(["fomcl", "yahoo.com"])
# Mac support added Oct-22-2011 by Rich Sadowsky "@".join(["rich", "richsad.com"])

from __future__ import with_statement # only Python 2.5
import sys
import os
import re
import ctypes
import struct
import operator
import math
import locale
import datetime
import time
import tempfile
import getpass

__author__  =  'Albert-Jan Roskam'
__version__ =  '3.0.0'

retcodes =    {0: 'SPSS_OK',
               1: 'SPSS_FILE_OERROR',
               2: 'SPSS_FILE_WERROR',
               3: 'SPSS_FILE_RERROR',
               4: 'SPSS_FITAB_FULL',
               5: 'SPSS_INVALID_HANDLE',
               6: 'SPSS_INVALID_FILE',
               7: 'SPSS_NO_MEMORY',
               8: 'SPSS_OPEN_RDMODE',
               9: 'SPSS_OPEN_WRMODE',
               10: 'SPSS_INVALID_VARNAME',
               11: 'SPSS_DICT_EMPTY',
               12: 'SPSS_VAR_NOTFOUND',
               13: 'SPSS_DUP_VAR',
               14: 'SPSS_NUME_EXP',
               15: 'SPSS_STR_EXP',
               16: 'SPSS_SHORTSTR_EXP',
               17: 'SPSS_INVALID_VARTYPE',
               18: 'SPSS_INVALID_MISSFOR',
               19: 'SPSS_INVALID_COMPSW',
               20: 'SPSS_INVALID_PRFOR',
               21: 'SPSS_INVALID_WRFOR',
               22: 'SPSS_INVALID_DATE',
               23: 'SPSS_INVALID_TIME',
               24: 'SPSS_NO_VARIABLES',
               27: 'SPSS_DUP_VALUE',
               28: 'SPSS_INVALID_CASEWGT',
               30: 'SPSS_DICT_COMMIT',
               31: 'SPSS_DICT_NOTCOMMIT',
               33: 'SPSS_NO_TYPE2',
               41: 'SPSS_NO_TYPE73',
               45: 'SPSS_INVALID_DATEINFO',
               46: 'SPSS_NO_TYPE999',
               47: 'SPSS_EXC_STRVALUE',
               48: 'SPSS_CANNOT_FREE',
               49: 'SPSS_BUFFER_SHORT',
               50: 'SPSS_INVALID_CASE',
               51: 'SPSS_INTERNAL_VLABS',
               52: 'SPSS_INCOMPAT_APPEND',
               53: 'SPSS_INTERNAL_D_A',
               54: 'SPSS_FILE_BADTEMP',
               55: 'SPSS_DEW_NOFIRST',
               56: 'SPSS_INVALID_MEASURELEVEL',
               57: 'SPSS_INVALID_7SUBTYPE',
               70: 'SPSS_INVALID_MRSETDEF',
               71: 'SPSS_INVALID_MRSETNAME',
               72: 'SPSS_DUP_MRSETNAME',
               -15: 'SPSS_EMPTY_DEW',
               -14: 'SPSS_NO_DEW',
               -13: 'SPSS_EMPTY_MULTRESP',
               -12: 'SPSS_NO_MULTRESP',
               -11: 'SPSS_NO_DATEINFO',
               -10: 'SPSS_NO_CASEWGT',
               -9: 'SPSS_NO_LABEL',
               -8: 'SPSS_NO_LABELS',
               -7: 'SPSS_EMPTY_VARSETS',
               -6: 'SPSS_NO_VARSETS',
               -5: 'SPSS_FILE_END',
               -4: 'SPSS_EXC_VALLABEL',
               -3: 'SPSS_EXC_LEN120',
               -2: 'SPSS_EXC_VARLABEL',
               -1: 'SPSS_EXC_LEN64'}

printTypes =  {1: ('SPSS_FMT_A', 'Alphanumeric'),
               2: ('SPSS_FMT_AHEX', 'Alphanumeric hexadecimal'),
               3: ('SPSS_FMT_COMMA', 'F Format with commas'),
               4: ('SPSS_FMT_DOLLAR', 'Commas and floating dollar sign'),
               5: ('SPSS_FMT_F', 'Default Numeric Format'),
               6: ('SPSS_FMT_IB', 'Integer binary'),
               7: ('SPSS_FMT_PIBHEX', 'Positive integer binary - hex'),
               8: ('SPSS_FMT_P', 'Packed decimal'),
               9: ('SPSS_FMT_PIB', 'Positive integer binary unsigned'),
               10: ('SPSS_FMT_PK', 'Positive integer binary unsigned'),
               11: ('SPSS_FMT_RB', 'Floating point binary'),
               12: ('SPSS_FMT_RBHEX', 'Floating point binary hex'),
               15: ('SPSS_FMT_Z', 'Zoned decimal'),
               16: ('SPSS_FMT_N', 'N Format- unsigned with leading 0s'),
               17: ('SPSS_FMT_E', 'E Format- with explicit power of 10'),
               20: ('SPSS_FMT_DATE', 'Date format dd-mmm-yyyy'),
               21: ('SPSS_FMT_TIME', 'Time format hh:mm:ss.s'),
               22: ('SPSS_FMT_DATE_TIME', 'Date and Time'),
               23: ('SPSS_FMT_ADATE', 'Date format dd-mmm-yyyy'),
               24: ('SPSS_FMT_JDATE', 'Julian date - yyyyddd'), 
               25: ('SPSS_FMT_DTIME', 'Date-time dd hh:mm:ss.s'),
               26: ('SPSS_FMT_WKDAY', 'Day of the week'),
               27: ('SPSS_FMT_MONTH', 'Month'),
               28: ('SPSS_FMT_MOYR', 'mmm yyyy'),
               29: ('SPSS_FMT_QYR', 'q Q yyyy'),
               30: ('SPSS_FMT_WKYR', 'ww WK yyyy'),
               31: ('SPSS_FMT_PCT', 'Percent - F followed by %'),
               32: ('SPSS_FMT_DOT', 'Like COMMA, switching dot for comma'),
               33: ('SPSS_FMT_CCA', 'User Programmable currency format'),
               34: ('SPSS_FMT_CCB', 'User Programmable currency format'),
               35: ('SPSS_FMT_CCC', 'User Programmable currency format'),
               36: ('SPSS_FMT_CCD', 'User Programmable currency format'),
               37: ('SPSS_FMT_CCE', 'User Programmable currency format'),
               38: ('SPSS_FMT_EDATE','Date in dd/mm/yyyy style'),
               39: ('SPSS_FMT_SDATE', 'Date in yyyy/mm/dd style')}

reversePrintTypes = dict([(fmt[0][9:], value)
                          for fmt, value in dict(zip(printTypes.values(),
                                                     printTypes.keys())).iteritems()])

######################################################################################

class Generic(object):

    def __init__(self):
        self.spssio, self.fopen = self.loadLibrary()
    
    def loadLibrary(self):
        """ This function loads the spss I/O file (.dll or .so file or dylib file) and opens
        the spss data file for reading."""
        platform = sys.platform.lower()
        if platform.startswith("win"):
            try:
                os.environ["PATH"] += ";" + os.path.abspath(".")
                spssio = ctypes.windll.spssio32
                libc = ctypes.cdll.msvcrt
                fopen = libc._fdopen # libc.fopen() won't work on windows
            except WindowsError, e:
                msg = "Cannot find spssio32.dll in '%s'.\n" % os.path.abspath(".") + \
                      "Py file and Dll should live in the same directory [%s]." % e
                raise Exception, msg
            return spssio, fopen
        elif platform.startswith("linux"):
            # add library search path to LD_LIBRARY_PATH environment variable
            # Type this in the terminal **before** running the program:
            # export LD_LIBRARY_PATH=/path/of/additional/sofiles
            # Then type: python nameOfWrapperToTheSpssReaderWriter.py
            if __name__ == "__main__":
                msg = "This program cannot be run directly. " + \
                      "Type in the terminal: export LD_LIBRARY_PATH=/path/of/libspssdio " + \
                      "Then type: python nameOfWrapperToTheSpssReaderWriter.py"
                raise Exception, msg
            spssio = ctypes.CDLL("libspssdio.so.1")        
            libc = ctypes.CDLL("libc.so.6")
            fopen = libc.fdopen
            return spssio, fopen
        elif platform.startswith("darwin"):
            # you must put all the dylib files that come with the IBM 
            # SPSS_Statistics_InputOutput_Modules_* package in the macos
            # directory somewhere that OS X can find them
            # one simple way to accomplish this is to copy them to /usr/lib
            spssio = ctypes.CDLL("libspssdio.dylib")        
            libc = ctypes.CDLL("libc.dylib")
            fopen = libc.fdopen
            return spssio, fopen
        else:
            msg = "Your platform ('%s') is not supported" % platform
            raise NotImplementedError, msg

    def loadSavFile(self, savFileName, spssio):
        """ This function opens IBM SPSS Statistics data files for reading and returns a handle that
        should be used for subsequent operations on the file. """
        if os.path.exists(savFileName):
            fh = self.fopen(savFileName, "rb")
            fhPtr = ctypes.byref(ctypes.c_int(fh))
            retcode = spssio.spssOpenRead(ctypes.c_char_p(savFileName), fhPtr)
            return retcode, fh
        else:
            raise Exception, "File '%s' does not exist!" % savFileName

    def conversionFormatCtoPy(self, varTypes, varNames):
        """ This function generates a struct format string for the conversion
        between C and Python values. SPSS data files are assumed to have either
        8-byte doubles/floats or n-byte chars[]/strings, where n is always
        8 bytes or a multiple thereof."""
        structFmt = ""
        if sys.byteorder == "little":
            endianness = "<"
        elif sys.byteorder == "big":
            endianness = ">"
        else:
            endianness = "@"
        structFmt += endianness
        for varName in varNames:
            varType = varTypes[varName]
            if varType == 0:
                structFmt += "d"
            else:
                fmt = str(int(math.ceil(int(varType) / 8.0) * 8))
                structFmt += fmt + "s"
        return structFmt

    def getSystemSysmisVal(self, spssio):
        """This function returns the IBM SPSS Statistics system-missing
        value for the host system."""
        try:
            sysmis = -1 * sys.float_info[0] # Python 2.6 and higher.
        except AttributeError:
            spssio.spssSysmisVal.restype = ctypes.c_float
            sysmis = spssio.spssSysmisVal()
        return sysmis

    def setInterfaceEncoding(self, spssio, interfaceEncoding):
        """This function sets the current interface encoding."""
        self.icodes = {"UTF-8": 0, "CODEPAGE": 1}
        interfaceEncoding = interfaceEncoding.upper()
        if interfaceEncoding not in self.icodes.keys():
            msg = "Invalid interface encoding ('%s'), valid values are 'UTF-8' or 'CODEPAGE'" % \
                  interfaceEncoding
            raise Exception, msg
        try:
            retcode = spssio.spssSetInterfaceEncoding(ctypes.c_int(self.icodes[interfaceEncoding]))
            return retcode
        except AttributeError:
            print "NOTE. Function 'setInterfaceEncoding' not found. You are using a .dll from SPSS < v16"
            return 0
    
    def getInterfaceEncoding(self, spssio):
        """This function returns the current interface encoding.
        ('UTF-8' or 'CODEPAGE') and the specific current codepage (e.g. cp1252)"""
        try:
            swapped = dict(zip(self.icodes.values(), self.icodes.keys()))
            interfaceEncoding = swapped[spssio.spssGetInterfaceEncoding()]
            encoding = locale.getpreferredencoding()if interfaceEncoding == "CODEPAGE" else "UTF-8"
            return interfaceEncoding, encoding
        except AttributeError:
            print "NOTE. Function 'setInterfaceEncoding' not found. You are using a .dll from SPSS < v16"
            return "UTF-8", "UTF-8"

    def encodeStringValues(self, record, fileEncoding, encoding):
        """ This function encodes string values in a record in the encoding
        of the SPSS data file. """
        encodedRecord = []
        for value in record:
            if isinstance(value, str):
                try:
                    value = value.decode(fileEncoding, "replace").encode(encoding)
                except UnicodeEncodeError:
                    value = value.decode(fileEncoding, "replace").encode("UTF-8")
            encodedRecord.append(value)
        return encodedRecord


######################################################################################

class SavReader(object):
    """ Read Spss system files (.sav)

    Parameters:
    -savFileName: the file name of the spss data file
    -returnHeader: Boolean that indicates whether the first record should
        be a list of variable names (default is True)
    -recodeSysmisTo: indicates to which value missing values should
        be recoded (default = ""),
    -selectVars: indicates which variables in the file should be selected.
        The variables should be specified as a list or a tuple of
        valid variable names. If None is specified, all variables
        in the file are used (default = None)
    -verbose: Boolean that indicates whether information about the spss data file
        (e.g., number of cases, variable names, file size) should be printed on
        the screen (default = True).
    -rawMode: Boolean that indicates whether values should get SPSS-style formatting,
        and whether date variables (if present) should be converted to ISO-dates. If True.
        the program does not format any values, which increases processing speed.
        (default = False)
    -interfaceEncoding: indicates the mode in which text communicated to or from the
        I/O Module will be. Valid values are 'UTF-8' or 'CODEPAGE' (default = 'CODEPAGE')

    Typical use:
    savFileName = "d:/someFile.sav"
    with SavReader(savFileName) as sav:
        header = sav.next()
        for line in sav:
            process(line)
    """

    def __init__(self, savFileName, returnHeader=True, recodeSysmisTo="",
                 verbose=True, selectVars=None, rawMode=False, interfaceEncoding="CODEPAGE"):
        """ Constructor. Initializes all vars that can be recycled """

        self.savFileName = savFileName
        self.returnHeader = returnHeader
        self.recodeSysmisTo = recodeSysmisTo
        self.verbose = verbose
        self.selectVars = selectVars
        self.rawMode = rawMode
        self.interfaceEncodingIn = interfaceEncoding
        
        self.gregorianEpoch = datetime.datetime(1582, 10, 14, 0, 0, 0)

        self.numVars = ctypes.c_int()
        self.numVarsPtr = ctypes.byref(self.numVars)
        self.nCases = ctypes.c_long()
        self.numofCasesPtr = ctypes.byref(self.nCases)

        self.attribNames = ctypes.c_char_p()
        self.attribText = ctypes.c_char_p()
        self.nAttributes = ctypes.c_int()
        self.attribNamesPtr = ctypes.byref(self.attribNames)
        self.attribTextPtr = ctypes.byref(self.attribText)
        self.nAttributesPtr = ctypes.byref(self.nAttributes)

        self.numValue = ctypes.c_double()
        self.numValuePtr = ctypes.byref(self.numValue)
        self.assumedCharWid = 200
        self.charValue = ctypes.create_string_buffer(self.assumedCharWid)
        self.charValuePtr = ctypes.byref(self.charValue)
        self.valueSize = ctypes.c_int(self.assumedCharWid)

        self.generic = Generic()
        self.spssio, self.fopen = self.generic.loadLibrary()
        self.sysmis = self.generic.getSystemSysmisVal(self.spssio)
        self.generic.setInterfaceEncoding(self.spssio, self.interfaceEncodingIn) or False
        self.retcode, self.fh = self.generic.loadSavFile(self.savFileName, self.spssio)

        self.SavDataDictionaryReader = SavDataDictionaryReader(self.savFileName)
  
        self.fileEncoding = self.getFileEncoding(self.fh)[1] or "UTF-8"
        self.fileCodePage = self.getFileCodePage(self.fh)[1] or locale.getpreferredencoding()
        #self.encoding = self.fileCodePage ## ???
        
        self.numVars_, self.nCases_, self.varNames, self.varTypes, self.printTypesFile, \
          self.printTypeLabels, self.varWids = self._readBasicSavFileInfo()
        self.structFmt = self.generic.conversionFormatCtoPy(self.varTypes, self.varNames)
        
        self.interfaceEncoding, self.encoding = self.generic.getInterfaceEncoding(self.spssio) or ("UTF-8", "UTF-8")
        self.header = self.getHeader(self.selectVars)

    def __enter__(self):
        """ This function opens the spss data file."""
        return self.readSavFile(self.returnHeader, self.recodeSysmisTo,
                                self.selectVars, self.rawMode, self.encoding)

    def __exit__(self, type, value, tb):
        """ This function closes the spss data file."""
        if type is not None:
            pass # Exception occurred
        self.spssio.spssCloseRead(self.fh)
        del self.spssio
        
    def _readBasicSavFileInfo(self):
        """ This function reads and returns some basic information of the open
        spss data file. It returns the following variables:
        retcode: the return code (0 means OK)
        spssio: the spss i/o C module, opened with ctypes.windll.spssio32
        fh: the file handle
        numVars: the number of variables in the spss data file
        nCases: the number of cases (records) in the spss data file
        varNames: a list of the var names  in the spss data file
        varTypes: a dictionary with var names as keys and var types as values
        printTypesFile: a dictionary with var names as keys and print types as values
        printTypeLabels: a dictionary with var names as keys and print type labels as values
        varWids: : a dictionary with var names as keys and var widths as values
        NOT FOR GENERAL USE; see getSavFileInfo
        """

        numVars = self.getNumberofVariables(self.fh, self.spssio)[1]
        nCases = self.getNumberofCases(self.fh, self.spssio)[1]
        varNames, varTypes_ = self.SavDataDictionaryReader.getVarInfo(self.fh, self.spssio)
        
        varTypes, printTypesFile, varWids, printDecs, \
                  printWids = {}, {}, {}, {}, {}
        for i, varName in enumerate(varNames):
            varTypes[varName] = varTypes_[i]
            retcode, printType, printDec, printWid = \
                     self.SavDataDictionaryReader.getVarPrintFormat(varName)
            printTypesFile[varName] = printType
            varWids[varName] = printWid
            printDecs[varName] = printDec
            printWids[varName] = printWid
            
        printTypeLabels = dict([(varName,
                                 printTypes[printType][0])
                                for varName, printType in printTypesFile.iteritems()])

        fmts = dict([(varName, printTypeLabels[varName].split("_")[-1])
                     for varName in varNames])
        if self.verbose:
            print self.getFileReport(self.savFileName, varNames, varTypes, fmts,
                               printDecs, printWids, nCases)

        return numVars, nCases, varNames, varTypes, printTypesFile, printTypeLabels, varWids

    def getSavFileInfo(self):
        """ This function reads and returns some basic information of the open
        spss data file. Returns numVars, nCases, varNames, varTypes, printTypesFile,
        printTypeLabels, varWids. Suitable for use without context manager ('with' statement)
        See also _readBasicSavFileInfo method."""
        return self.numVars_, self.nCases_, self.varNames, self.varTypes, self.printTypesFile, \
          self.printTypeLabels, self.varWids
            
    def getNumberofVariables(self, fh, spssio):
        """ This function reports the number of variables present in a data file."""
        retcode = spssio.spssGetNumberofVariables(fh, self.numVarsPtr)
        return retcode, self.numVars.value

    def getNumberofCases(self, fh, spssio):
        """ This function reports the number of cases present in a data file"""
        retcode = spssio.spssGetNumberofCases(fh, self.numofCasesPtr)
        return retcode, self.nCases.value

    def formatValue(self, fh, spssio, variable, value, printTypeLabel,
                    varWid, recodeSysmisTo):
        """ This function formats date fields to ISO dates (yyyy-mm-dd), plus
        some other date/time formats. The SPSS N format is formatted to a
        character value with leading zeroes."""
        supportedDates = {'SPSS_FMT_DATE':     '%Y-%m-%d',
                          'SPSS_FMT_JDATE':    '%Y-%m-%d',
                          'SPSS_FMT_EDATE':    '%Y-%m-%d',
                          'SPSS_FMT_SDATE':    '%Y-%m-%d',
                          'SPSS_FMT_DATE_TIME':'%Y-%m-%d %H:%M:%S',
                          'SPSS_FMT_WKDAY':    '%A %H:%M:%S',
                          'SPSS_FMT_ADATE':    '%Y-%m-%d',
                          'SPSS_FMT_WKDAY':    '%A',
                          'SPSS_FMT_MONTH':    '%B',
                          'SPSS_FMT_MOYR':     '%B %Y',
                          'SPSS_FMT_WKYR':     '%W WK %Y'}
        if printTypeLabel in supportedDates:
            fmt = supportedDates[printTypeLabel]
            return self.spss2strDate(value, fmt, recodeSysmisTo)
        elif printTypeLabel == 'SPSS_FMT_N':
            value = str(value).zfill(varWid)
            return value
        else:
            return value
    
    def spss2strDate(self, spssDateValue, fmt, recodeSysmisTo):
        """ This function converts internal SPSS dates (number of seconds
        since midnight, Oct 14, 1582 (the beginning of the Gregorian calendar))
        to a human-readable format """
        try:
            theDate = self.gregorianEpoch + datetime.timedelta(seconds=spssDateValue)
            return datetime.datetime.strftime(theDate, fmt)
        except TypeError:
            return recodeSysmisTo
        except ValueError:
            return recodeSysmisTo
        except OverflowError:
            return recodeSysmisTo

    def formatRecord(self, record, recodeSysmisTo):
        """ This function formats the values in a record according to the
        formats given in the SPSS file dictionary."""
        formattedRecord = []
        for rawValue, varName in zip(record, self.varNames):
            value = recodeSysmisTo if rawValue <= self.sysmis else rawValue
            if self.printTypeLabels[varName] != 'SPSS_FMT_F':
                value = self.formatValue(self.fh, self.spssio, varName, rawValue,
                                         self.printTypeLabels[varName],
                                         self.varWids[varName], recodeSysmisTo)
            formattedRecord.append(value)
        return formattedRecord
    
    def getFileEncoding(self, fh):
        """This function obtains the encoding applicable to a file.
        The encoding is returned as an IANA encoding name, such as
        ISO-8859-1. """
        self.pszEncoding = ctypes.create_string_buffer(20) # is 20 enough??
        self.pszEncodingPtr = ctypes.byref(self.pszEncoding)
        try:
            retcode = self.spssio.spssGetFileEncoding(self.fh, self.pszEncodingPtr)
            return retcode, self.pszEncoding.value
        except AttributeError:
            print "Function 'getFileEncoding' not found. You are using a .dll from SPSS < v16"
            return False, False

    def getFileCodePage(self, fh):
        """This function provides the Windows code page
        number of the encoding applicable to a file.""" 
        try:
            self.nCodePage = ctypes.c_int()
            self.nCodePagePtr = ctypes.byref(self.nCodePage)
            retcode = self.spssio.spssGetFileCodePage(self.fh, self.nCodePagePtr)
            return retcode, self.nCodePage.value
        except AttributeError:
            print "function 'spssGetFileCodePage' not found. You are using a .dll from SPSS < v16"
            return False, False
        
    def getFileReport(self, savFileName, varNames, varTypes, fmts, printDecs,
                      printWids, nCases):
        """ This function prints a report about basic file characteristics """
        bytes = os.path.getsize(savFileName)
        kb = float(bytes) / 2**10
        mb = float(bytes) / 2**20
        (fileSize, label) = (mb, "MB") if mb > 1 else (kb, "kB")
        line1 = [os.linesep + "*" * 70]
        line2 = ["*File '%s' (%5.2f %s) has %s columns (variables) and %s rows (%s values)" % \
              (savFileName, fileSize, label, len(varNames), nCases, len(varNames) * nCases)]
        line3 = ["*The file encoding is: %s (Code Page: %s)" % (self.fileEncoding, self.fileCodePage)]
        loc, cp = locale.getlocale()
        line4 = ["*Your computer's locale is: %s (Code page: %s)" % (loc, cp)]
        line5 = ["*The file contains the following variables:"]
        lines = []
        for cnt, varName in enumerate(varNames):
            label = "string" if varTypes[varName] > 0 else "numerical"
            lines.append("%03d. %s (%s%d.%d - %s)" % (cnt+1, varName, fmts[varName], \
                                                      printWids[varName], printDecs[varName], label))
        lineN = ["*" * 70]
        report = os.linesep.join(line1 + line2 + line3 + line4 + line5 + lines + lineN)
        return report

    def getCaseBuffer(self):
        """ This function returns a buffer and a pointer to that buffer. A whole
        case will be read into this buffer."""
        self.caseSize = ctypes.c_long()
        self.caseSizePtr = ctypes.byref(self.caseSize)
        self.retcode = self.spssio.spssGetCaseSize(self.fh, self.caseSizePtr)
        self.caseBuffer = ctypes.create_string_buffer(self.caseSize.value)
        self.caseBufferPtr = ctypes.byref(self.caseBuffer)
        return self.caseBuffer, self.caseBufferPtr

    def getHeader(self, selectVars):
        if selectVars is None:
            header = self.varNames
        elif isinstance(selectVars, (list, tuple)):
            diff = set(selectVars).difference(set(self.varNames))
            if diff:
                msg = "Variable names misspecified ('%s')" % ", ".join(diff)
                raise Exception, msg
            varPos = [self.varNames.index(v) for v in self.varNames if v in selectVars]
            self.selector = operator.itemgetter(*varPos)
            header = self.selector(self.varNames)
            header = [header] if not isinstance(header, tuple) else header
        else:
            raise Exception, "Variable names list misspecified. " + \
                  "Must be 'None' or a list or tuple of existing variables"    
        return header

    def readSavFile(self, returnHeader, recodeSysmisTo, selectVars, rawMode, encoding):
        """ This is the main function of this class. It is a generator, which
        returns one record of the spss data file at a time. """
        
        debug = False
        if retcodes[self.retcode] == "SPSS_OK":
            if returnHeader:
               yield self.header

            # avoiding dots inside the loops
            # http://wiki.python.org/moin/PythonSpeed/PerformanceTips#Avoiding_dots...
            containsStringvars = max([varType for varName, varType in self.varTypes.items()
                                      if varName in self.header]) > 0
            self.caseBuffer, self.caseBufferPtr = self.getCaseBuffer()
            unpack = struct.unpack
            wholeCaseIn = self.spssio.spssWholeCaseIn
            print "Pct progress ...",
            for case in range(self.nCases_):
                retcode = wholeCaseIn(self.fh, self.caseBufferPtr)
                if retcodes[retcode] != 'SPSS_OK':
                    print "WARNING: Record %s is faulty" % case+1
                    continue
                record = unpack(self.structFmt, self.caseBuffer.raw)
                if selectVars is not None:
                    record = self.selector(record)
                    record = [record] if not isinstance(record, tuple) else record
                if containsStringvars:
                    record = self.generic.encodeStringValues(record, self.fileEncoding, encoding)
                if not rawMode:
                    record = self.formatRecord(record, self.recodeSysmisTo)
                if debug and (case+1) % 10 == 0:        
                    print "record", case+1, record
                pctProgress = (float(case) / self.nCases_) * 100
                if pctProgress % 5 == 0:
                    print "%2.1f%%... " % pctProgress,
                yield record
        else: 
            try:
                print "Error", retcodes[retcode]
            except KeyError:
                print "Unknown error code (%d)" % retcode
            finally:
                raise Exception, "You fail!"

######################################################################################
            
class SavWriter(object):

    """ Write Spss system files (.sav)

    Parameters:
    -savFileName: the file name of the spss data file
    -varNames: list or a tuple with the variable names of the spss data file.
    -varTypes: varTypes dictionary {varName: varType}, where varType == 0 means 'numeric',
      and varType > 0 means 'character' of that length
    -printTypesFile: optional printType dictionary {varName: spssFmt} (default: None)
    -overwrite: Boolean that indicates whether an existing Spss file should be overwritten
      (default: True)


    """

    def __init__(self, savFileName, varNames, varTypes, printTypesFile=None,
                 varLabels=None, valueLabels=None, overwrite=True,
                 interfaceEncoding="CODEPAGE"):
        """ Constructor. Initializes all vars that can be recycled """

        self.savFileName = savFileName
        self.varNames = varNames
        self.varTypes = varTypes
        self.printTypesFile = printTypesFile
        self.overwrite = overwrite
        self.interfaceEncodingIn = interfaceEncoding

        self.generic = Generic()
        self.structFmt = self.generic.conversionFormatCtoPy(self.varTypes, self.varNames)
        self.spssio, self.fopen = self.generic.loadLibrary()
        self.sysmis = self.generic.getSystemSysmisVal(self.spssio)
        self.generic.setInterfaceEncoding(self.spssio, self.interfaceEncodingIn) or False
        
        self.fh = self.openWrite(self.savFileName, self.overwrite)[1]
        self.setVarNames(self.fh, self.varNames, self.varTypes)

        self.savDataDictionaryWriter = SavDataDictionaryWriter(self.fh, self.spssio, self.varNames, self.varTypes)
        self.savDataDictionaryWriter.setVarLabels(self.fh, self.spssio, varLabels)
        self.savDataDictionaryWriter.setValueLabels(self.fh, self.spssio, valueLabels)
        self.savDataDictionaryWriter.setVarPrintFormats(self.fh, self.varNames, self.varTypes, self.printTypesFile)
        
        self.commitHeader(self.fh)
        self.getCaseSize(self.fh)
        self.wholeCaseOut = self.spssio.spssWholeCaseOut
        
    def __enter__(self):
        """ This function returns the writer object itself so the writerow and
        the writerows methods become available for use with 'with' statements."""
        return self

    def __exit__(self, type, value, tb):
        """ This function closes the spss data file."""
        if type is not None:
            pass # Exception occurred
        self.spssio.spssCloseWrite(self.fh)
        del self.spssio

    def openWrite(self, savFileName, overwrite):
        """ This function opens a file in preparation for creating a new IBM SPSS Statistics data
        file and returns a handle that should be used for subsequent operations on the file."""
        
        if overwrite or not os.path.exists(savFileName):
            fh = self.fopen(self.savFileName, "wb")
            fhPtr = ctypes.byref(ctypes.c_int(fh))
            retcode = self.spssio.spssOpenWrite(ctypes.c_char_p(savFileName), fhPtr)
            compSwitch = ctypes.c_int(1) # compress file by default
            self.spssio.spssSetCompression(fh, compSwitch)
            #modified by RSS to get username from getpass.getuser() function
            idString = "File created by user '%s' at %s"[:64] % \
                       (getpass.getuser(), time.asctime())
            self.spssio.spssSetIdString(fh, ctypes.create_string_buffer(idString))
            return retcode, fh
        elif not overwrite and os.path.exists(savFileName):
            raise Exception, "File '%s' already exists!" % self.savFileName

    def setVarNames(self, fh, varNames, varTypes):
        """ For each element of the dictionary VarTypes, this function creates a new variable
        named varName (the dictionary key), which will be either numeric or string based on
        varLength (the dictionary value). If the latter is zero, a numeric variable with a default
        format of F8.2 will be created; if it is greater than 0 and less than or equal to 32767,
        a string variable with length varLength will be created; any other value will be rejected as
        invalid."""
        for varName in varNames:
            varLength = varTypes[varName]
            retcode = self.spssio.spssValidateVarname(varName)
            msg = "invalid variable name (%s)[%s]" % (varName, retcodes[retcode])
            if retcode != 0:
                raise Exception, msg
            else:
                retcode2 = self.spssio.spssSetVarName(fh, varName, varLength)
                if retcode != 0:
                    raise Exception, retcodes[retcode2]

    def commitHeader(self, fh):
        """This function writes the data dictionary to the data file associated with file handle 'fh'.
        Before any case data can be written, the dictionary must be committed; once the dictionary has
        been committed, no further changes can be made to it."""
        retcode = self.spssio.spssCommitHeader(fh)
        return retcode

    def getCaseSize(self, fh):
        """ This function reports the size of a raw case record for the file associated with handle.
        The case size is reported in bytes."""
        caseSize = ctypes.c_int()
        caseSizePtr = ctypes.byref(caseSize)
        retcode = self.spssio.spssGetCaseSize(fh, caseSizePtr)
        return retcode, caseSize.value

    def writerow(self, record):
        """ This function writes one record, which is a Python list."""
        convertedRecord = []
        for value, varName in zip(record, self.varNames):
            charlen = self.varTypes[varName]
            if charlen > 0:
                value = value.ljust(charlen)
            else:
                try:
                    value = float(value)
                except ValueError:
                    value = self.sysmis
            convertedRecord.append(value)
        convertedRecord = self.generic.encodeStringValues(convertedRecord, "UTF-8", "UTF-8")
        retcode = self.wholeCaseOut(self.fh, struct.pack(self.structFmt, *convertedRecord))
        return retcode

    def writerows(self, records):
        """ This function writes all records."""
        for record in records:
            print self.varNames
            retcode = self.writerow(record)
            if retcode < 0:
                print "Warning: %s" % retcodes[retcode]
            elif retcode > 0:
                raise Exception, "Error writing records. File in use? ('%s')" % \
                      retcodes[retcode]

    def close(self):
        self.__exit__(None, '', '')


##################################################################################

class SavDataDictionaryReader(object):
    """ This class contains methods that read the data dictionary of an SPSS data file.
    This yields the same information as the Spss command 'DISPLAY DICTIONARY' (although
    not all dictionary items are implemented. NB: do not confuse an Spss dictionary with
    a Python dictionary!"""

    def __init__(self, savFileName):
        """ Constructor. Initializes all vars that can be recycled """

        self.savFileName = savFileName
        self.numVars = ctypes.c_int()
        self.numVarsPtr = ctypes.byref(self.numVars)

        self.printType = ctypes.c_int()
        self.printDec = ctypes.c_int()
        self.printWid = ctypes.c_int()
        self.printTypePtr = ctypes.byref(self.printType)
        self.printDecPtr = ctypes.byref(self.printDec)
        self.printWidPtr = ctypes.byref(self.printWid)
        
        self.generic = Generic()
        self.spssio, self.fopen = self.generic.loadLibrary()
        self.retcode, self.fh = self.generic.loadSavFile(self.savFileName, self.spssio)
 
        self.varNames, self.varTypes = self.getVarInfo(self.fh, self.spssio)
        self.varNamesTypes = dict([(varName, varType) for varName, varType in zip(self.varNames, self.varTypes)])

    def __enter__(self):
        """ This function returns the DictionaryReader object itself so its methods
        become available for use with context managers ('with' statements)."""
        return self

    def __exit__(self, type, value, tb):
        """ This function closes the spss data file and does some cleaning."""
        if type is not None:
            pass # Exception occurred
        self.spssio.spssCloseRead(self.fh)
        del self.spssio

    def getVarNameAndType(self, fh, spssio, iVar):
        """ Get variable name and type. The variable type code is an integer
        in the range 0-32767, 0 indicating a numeric variable and a positive
        value indicating a string variable of that size."""
        varNameBuff = ctypes.create_string_buffer(65)
        varNamePtr = ctypes.byref(varNameBuff)
        varType = ctypes.c_int()
        varTypePtr = ctypes.byref(varType)
        retcode = spssio.spssGetVarInfo(fh, iVar, varNamePtr, varTypePtr)
        return varNameBuff.value, varType.value

    def getVarInfo(self, fh, spssio):
        """ This function gets the name and type of one of the variables
        present in a data file."""
        spssio.spssGetNumberofVariables(fh, self.numVarsPtr)
        varNames, varTypes = [], []
        for iVar in range(self.numVars.value):
            varName, varType = self.getVarNameAndType(fh, spssio, iVar)
            varNames.append(varName)
            varTypes.append(varType)
        return varNames, varTypes
        
    def getVarLabel(self, varName):
        """ This function reports the Spss variable label, as defined by the
        Spss command "VARIABLE LABEL varName 'varLabel'." """
        MAX_SHORT_VARLABEL_LEN = 120 # fixed
        MAX_LONG_VAR_LEN = 1000      # allow variable labels of up to 1000 bytes
        varLabelBuff = ctypes.create_string_buffer(MAX_SHORT_VARLABEL_LEN + 1)
        varLabelPtr = ctypes.byref(varLabelBuff)
        retcode = self.spssio.spssGetVarLabel(self.fh, varName, varLabelPtr)
        varLabel = varLabelBuff.value
        if varLabel and len(varLabel) > MAX_SHORT_VARLABEL_LEN:
            lenBuff = MAX_LONG_VAR_LEN
            varLabelBuff = ctypes.create_string_buffer(lenBuff)
            varLabelBuffPtr = ctypes.byref(varLabelBuff)
            lenLabelPtr = ctypes.byref(ctypes.c_int())
            retcode = self.spssio.spssGetVarLabelLong (self.fh, varName, varLabelBuffPtr, lenBuff, lenLabelPtr)
            varLabel = varLabelBuff.value
        varLabel = unicode(varLabel, "utf-8")
        return retcode, varName, varLabel

    def getValueLabels(self, varName):
        """This function gets the set of labeled values and associated labels for a short string
        variable or a numeric variable"""

        try:
            isNumVar = self.varNamesTypes[varName] == 0
        except KeyError:
            msg = "Variable '%s' does not exist!" % varName
            raise Exception, msg

        MAX_ARRAY_SIZE = 1000 # assume never more than 1000 labels        
        numLabels = ctypes.c_int()        
        numLabelsPtr = ctypes.byref(numLabels)
        if isNumVar:
            # Pointer to array of pointers double values
            valuesPtr = ctypes.pointer((ctypes.POINTER(ctypes.c_double) * MAX_ARRAY_SIZE)())
            # Pointer to array of pointers to labels
            labelsPtr = ctypes.pointer((ctypes.POINTER(ctypes.c_char_p) * MAX_ARRAY_SIZE)())
            retcode = self.spssio.spssGetVarNValueLabels(self.fh, varName, valuesPtr, labelsPtr, numLabelsPtr)
        else:
            valuesPtr = ctypes.pointer((ctypes.POINTER(ctypes.c_char_p) * MAX_ARRAY_SIZE)())
            labelsPtr = ctypes.pointer((ctypes.POINTER(ctypes.c_char_p) * MAX_ARRAY_SIZE)())
            retcode = self.spssio.spssGetVarCValueLabels(self.fh, varName, valuesPtr, labelsPtr, numLabelsPtr)
        valueLabels = {}
        for i in range(numLabels.value):
            value = valuesPtr.contents[0][i]
            label = labelsPtr.contents[0][i]
            if isinstance(value, str):
                value = unicode(value, "utf-8")
                label = unicode(label, "utf-8")
            valueLabels[value] = label

        # clean up (dunno yet why this crashes under Linux)
        if sys.platform.lower().startswith("win"):
            self.spssio.spssFreeVarNValueLabels(valuesPtr, labelsPtr, numLabels)
            self.spssio.spssFreeVarCValueLabels(valuesPtr, labelsPtr, numLabels)
 
        return retcode, valueLabels
    
    def getVarPrintFormat(self, varName):
        """ This function reports the print format of a variable. Format
        type, number of decimal places, and field width are returned. """
        self.varName = ctypes.c_char_p(varName)
        retcode = self.spssio.spssGetVarPrintFormat(self.fh,
                                self.varName,
                                self.printTypePtr,
                                self.printDecPtr,
                                self.printWidPtr)
        return retcode, self.printType.value, self.printDec.value, \
               self.printWid.value

    def dataDictionary(self):
        """ This function returns all the dictionary items. It returns
        a Python dictionary based on the Spss dictionary of the given
        Spss file. This is equivalent to the Spss command 'DISPLAY
        DICTIONARY'. Currently only valueLabels, variableLabels, and
        printFormats are implemented."""
        dataDictionary = {}
        for varName in self.varNames:
            valueLabels = {varName: self.getValueLabels(varName)[1]}
            variableLabels = {varName: self.getVarLabel(varName)[-1]}
            printType, printDec, printWid = self.getVarPrintFormat(varName)[1:]
            fmt = printTypes[printType][0].split("_")[-1] + str(printWid) + "." + str(printDec)
            printFormats = {varName: fmt}
            try:
                dataDictionary["valueLabels"].append(valueLabels)
                dataDictionary["variableLabels"].append(variableLabels)
                dataDictionary["printFormats"].append(printFormats)
            except KeyError:
                dataDictionary["valueLabels"] = [valueLabels]
                dataDictionary["variableLabels"] = [variableLabels]
                dataDictionary["printFormats"] = [printFormats]
        return dataDictionary
        
    def reportSpssDataDictionary(self, dataDict):
        """ This function reports (prints) information from the dictionary
        of the active Spss dataset. The parameter 'dataDict' is the return
        value of dataDictionary()"""
        for kwd, items in dataDict.items():
            for item in dataDict[kwd]:
                for n, (varName, v) in enumerate(item.items()):
                    if n == 0:
                        print "\n* %s of variable '%s'" % (kwd.upper(), varName.upper())
                    try:
                        for value, label in v.items():
                            print "%s -- %s" % (value, label)
                    except AttributeError:
                        print "%s -- %s" % (varName, v)

##################################################################################

class SavDataDictionaryWriter(object):
    """ This class allows some of the Spss data dictionary items to be set.
    None of the methods here should be called directly. All of them are used inside
    the SavWriter class"""

    def __init__(self, fh, spssio, varNames, varTypes):
        """ Constructor. Initializes all vars that can be recycled """
        self.varNames = varNames
        self.varTypes = varTypes.keys()
        self.varNamesTypes = varTypes
        self.generic = Generic()
        self.spssio, self.fopen = self.generic.loadLibrary()
        
    def setVarLabels(self, fh, spssio, varLabels=None):
        """ This function sets the label of a variable."""
        if varLabels:
            for varName, varLabel in varLabels.iteritems():
                retcode = spssio.spssSetVarLabel(fh, ctypes.c_char_p(varName), ctypes.c_char_p(varLabel))
                if retcode != 0:
                    print "NOTE. Problem with setting variable label '%s' of variable '%s' (%s)" \
                          % (varLabel, varName, retcodes[retcode])

    def setValueLabels(self, fh, spssio, allValueLabels):
        """ This function changes or adds the value labels of the
        values of a variable. The allValueLabels should be specified as a
        Python dictionary {varName: {value: valueLabel} or as None"""
        if allValueLabels:
            for varName, valueLabels in allValueLabels.iteritems():
                if valueLabels:
                    isNumeric = self.varNamesTypes[varName] == 0
                    for value, valueLabel in valueLabels.iteritems():
                        if isNumeric:
                            retcode = spssio.spssSetVarNValueLabel(fh, ctypes.c_char_p(varName),\
                                                                   ctypes.c_double(value), \
                                                                   ctypes.c_char_p(valueLabel))
                        else:
                            retcode = spssio.spssSetVarCValueLabel(fh, ctypes.c_char_p(varName),\
                                                               ctypes.c_char_p(value), \
                                                                   ctypes.c_char_p(valueLabel))
                        if retcode != 0:
                            print "NOTE. Problem with setting value labels of variable %s ('%s')"  % \
                                  (varName, retcodes[retcode])
               
    def setVarPrintFormats(self, fh, varNames, varTypes, printTypesFile):
        """ This function sets the print format of the variables."""
        # needs some refactoring ;-)
        setPrintFmt = self.spssio.spssSetVarPrintFormat
        if printTypesFile is not None:
            if isinstance(printTypesFile, dict):
                regex = re.compile("([A-Z]+)(\d+)\.*(\d*)")                      
                for varName in varNames:
                    varType = varTypes[varName]
                    thePrintType = printTypesFile[varName]
                    m = re.search(regex, printTypesFile[varName])
                    legalValues = [value[0][9:] for value in printTypes.values()]
                    theValue = re.sub("[0-9.]+", "", thePrintType)
                    if varType == 0 and m and theValue in legalValues:
                        printType = reversePrintTypes[m.group(1)]
                        printDec = 0 if not m.group(3) else int(m.group(3))
                        printWid = int(m.group(2))
                        retcode = setPrintFmt(fh, ctypes.create_string_buffer(varName),
                                                  ctypes.c_int(printType),
                                                  ctypes.c_int(printDec),
                                                  ctypes.c_int(printWid))
                        if retcodes[retcode] == "SPSS_INVALID_PRFOR": # = invalid PRint FORmat
                            if m and theValue not in legalValues:
                                msg = "Unknown printType format ('%s'), legal prefixes are: %s" % \
                                (theValue, ", ".join(legalValues))
                            elif m and printDec >= printWid:
                                msg = "PrintType error: variable width greater or equal " + \
                                "than number of decimals (variable '%s' has impossible " % varName + \
                                "format '%s%s.%s')" % (theValue, printWid, printDec)
                            elif not m:
                                msg = "PrintType misspecified ('%s')" % thePrintType
                            raise Exception, msg
            else:
                msg = """PrintTypes should be specified as a dictionary {'varname': printType}
                      For example: {'v1': 'F2.2', 'v2': 'A30'}"""
                raise Exception, msg
        else:
            warning = "NOTE. No printTypes specified, using defaults"


######################################################################################

if __name__ == "__main__":

    import contextlib, csv

    #savFileName = r"C:\Program Files\IBM\SPSS\Statistics\19\Samples\English\Employee data.sav"
    savFileName = "c:/program files/spss/employee data.sav"
    tempdir = tempfile.gettempdir() # changed to std function for Mac compatibilityos.environ["TEMP"]
    
    ## ---------------------------------                       
    ## SAV READER
    ## ---------------------------------

    ## ----- Get some basic file info
    numVars, nCases, varNames, varTypes, printTypesFile, printTypeLabels, varWids = \
             SavReader(savFileName).getSavFileInfo()

    ## ----- Typical use    
    with SavReader(savFileName, selectVars=['id'], recodeSysmisTo=999) as sav:
        header = sav.next()
        for line in sav:
            pass # do stuff

    ## ----- Convert file to .csv
    csvFileName = os.path.join(tempdir, "test_out.csv")
    with contextlib.nested(SavReader(savFileName, selectVars=None, verbose=True,
                                     rawMode=False, interfaceEncoding="UTF-8"),
                           open(csvFileName, "wb")) as (sav, f):
        writer = csv.writer(f)
        for line in sav:
            writer.writerow(line)
        print "Done! Csv file written: %s" % f.name
        
    ## ---------------------------------
    ## SAV WRITER
    ## ---------------------------------
    
    ## ----- Write many rows
    records = [['Test1', 1, 1], ['Test2', 2, 1]]
    varNames = ['var1', 'v2', 'v3']
    varTypes = {'var1': 5, 'v2': 0, 'v3': 0}
    printTypesFile = {'var1': 'A41', 'v2': 'F3.1', 'v3': 'F5.1'}
    varLabels = {'var1': 'This is variable 1', 'v2': 'This is v2!'}
    valueLabels = {'var1': {'Test1': 'Test1 value label',
                            'Test2': 'Test2 value label'},
                   'v2': {1: 'yes',
                          2: 'no'}}
    # ... printTypesFile, varLabels, valueLabels may also be None (default)
    savFileName = os.path.join(tempdir, "test.sav")
    with SavWriter(savFileName, varNames, varTypes,
                   printTypesFile, varLabels, valueLabels) as sav:
        sav.writerows(records)
        print "Done! %s" % sav.savFileName

    ## ----- Write one row
    savFileName = os.path.join(tempdir, "test2.sav")
    csvFileName = os.path.join(tempdir, "test.csv")
    varNames = ['var1', 'var2', 'var3']
    # ... var1 is a 50-char string var, the others are numerical:
    varTypes = {'var1': 50, 'var2': 0, 'var3': 0} 
    if os.path.exists(csvFileName):
        with contextlib.nested(SavWriter(savFileName, varNames, varTypes),
                               open(csvFileName, "rb")) as (sav, f):
            reader = csv.reader(f)
            header = reader.next()
            for row in reader:
                sav.writerow(row)
            print "Done! %s" % sav.savFileName

   ## ---------------------------------                       
   ## SAV DATA DICTIONARY READER
   ## ---------------------------------

    #savFileName = r"C:\Program Files\IBM\SPSS\Statistics\19\Samples\English\anorectic.sav"
    savFileName = "c:/program files/spss/employee data.sav"
    with SavDataDictionaryReader(savFileName) as spssDict:
        for varName in spssDict.varNames:
            print spssDict.getValueLabels(varName)[1]
            print spssDict.getVarLabel(varName)[1]
        wholeDict = spssDict.dataDictionary()
        print wholeDict["valueLabels"]
        print wholeDict["variableLabels"]
        spssDict.reportSpssDataDictionary(wholeDict)
