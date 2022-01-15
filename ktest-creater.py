import sys
import os
import struct

class KTestRepack(object):
    header = b"KTEST"
    version = struct.pack(">i", 2)
    numArgs = struct.pack(">i", 1)
    symArgvs = struct.pack(">i", 0)
    symArgvLen = struct.pack(">i", 0)
    chars = {1:"B", 2:"H", 4:"I", 8:"L", 16:"Q"}

    def __init__(self, grammar):
        self.grammar = grammar

        self.types = {
            "int1":self.int8gen, "functionptr":self.int8gen, "int8":self.int8gen, 
            "int16":self.int16gen, "int32":self.int32gen, "size":self.int32gen, 
            "int64":self.int64gen, "double":self.int64gen, "x86float":self.x86floatgen, 
            "array [":self.arraygen, "struct [":self.structgen, "structptr [":self.structgen 
        }
        
        self.objs = []
        self.ctr = 0

        while True:
            next_token = self.get_next()
            if next_token == "EOF":
                break
            self.types[next_token]()

    def get_data_from_file(self, num_bytes : int, name : str):
        data = input(f"Enter data for {name}: ")
        data = data.strip()
        if data == "":
            data = "2"
        char = self.chars[num_bytes]
        if data.startswith("0x"):
            data = data[2:]
            data = struct.pack(f"<{char}", int(data, 16))
        else:
            data = int(data)
            data = struct.pack(f"<{char}", data)
        name = input(f"Enter name of object : ").strip()
        return data, name

    def write_to_file(self, filename):
        try:
            f = open(filename, 'wb')
        except IOError:
            print(f"ERROR: file {filename} not found")
            sys.exit(-1)
        # write to file
        # First the header
        f.write(self.header)
        # write the version
        f.write(self.version)
        # Num Args
        f.write(self.numArgs)
        # File name
        f.write(struct.pack(">i", len(filename)))
        f.write(filename.encode())
        # symArgs
        f.write(self.symArgvs)
        f.write(self.symArgvLen)
        # Object
        f.write(struct.pack(">i", len(self.objs)))
        for obj in self.objs:
            # Name
            f.write(struct.pack(">i", len(obj.name)))
            f.write(obj.name.encode())
            f.write(struct.pack(">i", len(obj.data)))
            f.write(obj.data)
        
        # we are done
        f.close()

    def get_next(self):
        if self.ctr >= len(self.grammar):
            return "EOF"
        curr_line = self.grammar[self.ctr].strip()
        if curr_line == "":
            self.ctr += 1
            return self.get_next()
        self.ctr += 1
        return curr_line 

    def int8gen(self):
        self.objs.append(KTestObject(self.get_data_from_file(1, "int8"), 1))

    def int16gen(self):
        self.objs.append(KTestObject(self.get_data_from_file(2, "int16"), 2))
    
    def int32gen(self):
        self.objs.append(KTestObject(self.get_data_from_file(4, "int32"), 4))

    def int64gen(self):
        self.objs.append(KTestObject(self.get_data_from_file(8, "int64"), 8))

    def x86floatgen(self):
        self.objs.append(KTestObject(self.get_data_from_file(16, "x86float"), 16))
    
    def arraygen(self):
        # Increment and sanity check the size
        size_bytes = self.get_data_from_file(4, "array size")
        size = struct.unpack("<I", size_bytes[0])[0]
        self.objs.append(KTestObject(size_bytes, 4))

        size_field = self.get_next()

        if size == 0:
            # This is a special case, we can't do anything else
            size = 1
        
        element_type = self.get_next()
        for _ in range(size - 1):
            self.types[element_type]()
        
        # Now sanity check that the next step is closed brackets
        assert self.get_next() == "]", f"Array not closed"

    def structgen(self):
        # loop until closing brackets
        while True:
            next_token = self.get_next()
            if next_token == "]":
                break
            self.types[next_token]()
    
obj_ctr = 0

class KTestObject(object):
    def __init__(self, data, size, name = ""):
        global obj_ctr
        if isinstance(data, tuple):
            data, name = data
        if name == "":
            self.name = "name" + str(obj_ctr)
            obj_ctr = obj_ctr + 1
        else:
            self.name = name

        if len(data) != size:
            data = data + b'\0' * (size - len(data))
        self.data = data

    def __str__(self):
        stri  = f" Object : {self.name} \n"
        stri += f" Size   : {len(self.data)} \n"
        stri += f" Data   : {self.data} \n"
        return stri


if __name__ == "__main__":
    if len(sys.argv) > 1:
        inp_file = sys.argv[1]
        grammar = open(inp_file, "r").read()
    else: 
        print("Enter target grammar (ctrl-d to stop): ")
        grammar = sys.stdin.read()
    
    print("Starting input generation...")
    ktest_obj = KTestRepack(grammar.split("\n"))

    output_file = input("Enter output file name: ")
    if output_file == "":
        output_file = "output.ktest"
    ktest_obj.write_to_file(os.path.join(os.getcwd(), output_file))