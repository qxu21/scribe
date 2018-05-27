import os
import os.path
import re
import json

def msg_to_json(msg):
    uend = msg.find("#")
    print("Processing " + msg)
    if msg[20] == "]":
        # no edited timestamp
        #[2018-02-23T02:28:23] SpockMan02#4611: Coolio
        #0123456789012345678901234567890123456789
        b = {
                "id": None,
                "timestamp": msg[1:20],
                "author_name": msg[22:uend],
                "author_discrim": msg[uend+1:uend+5],
                "content": msg[uend+7:],
                "pinner_id":  None,
                "pin_timestamp": None}
    elif len(msg) > 47 and msg[47] == "]":
        #[2018-02-23T02:28:23 edited 2018-02-23T02:28:36] SpockMan02#4611: Coolio
        #01234567890123456789012345678901234567890123456789
        b = {
                "id": None,
                "timestamp": msg[1:20],
                "edited_timestamp": msg[28:47],
                "author_name": msg[49:uend],
                "author_discrim": msg[uend+1:uend+5],
                "content": msg[uend+7:],
                "pinner_id":  None,
                "pin_timestamp": None}
    else:
        print(msg)
        raise RuntimeError
    b["attachments"] = []
    if "\nATTACHMENT: " in msg:
        for a in msg.split("\nATTACHMENT: ")[1:]:
            b["attachments"].append(a)
    print("Result: " + ", ".join(["{}: {}".format(k, v) for k, v in b.items()]))
    return b

pindir = os.path.join(os.getcwd(),'old_pins')
outdir = os.path.join(os.getcwd(),'pins')
print("Found pindir at " + pindir)
for serverdir in os.listdir(pindir):
    print("Executing in server directory " + serverdir)
    for fi in os.listdir(os.path.join(pindir, serverdir)):
        print("Parsing file " + fi)
        if not fi.endswith(".txt"):
            continue
        with open(os.path.join(pindir, serverdir, fi)) as f:
            t = f.read()
        # list of blocks that need to be crunched into bricks due to old format suck
        protobricks = re.split(r'\n{2,}',t) 
        bricks_list = [] # list of bricks
        # crunch protobricks into bricks
        for brick in protobricks:
            if (not brick.startswith("[")) and len(bricks_list) != 0:
                bricks_list[-1] += "\n\n" + brick
            else:
                bricks_list.append(brick)
        bricks = [] # list of (brick, bool) - true if quote
        json_out = []
        for brick in bricks_list:
            isquote = False
            isfirst = True
            for l in brick.split('\n'):
                if l.startswith("[") and not isfirst:
                    isquote = True
                    break
                isfirst = False
            if isquote:
                protomsgs = re.split(r"(\n\[.{19,50}?])", brick)
                msgs = [protomsgs[0]]
                for n in range(1,len(protomsgs),2):
                    #print("n="+str(n))
                    #print("Joining" + protomsgs[n] + protomsgs[n+1])
                    msgs.append(protomsgs[n][1:] + protomsgs[n+1])
                print("msgs: " + str(msgs))
                q = [msg_to_json(msgs[0])]
                # i have regrets
                for m in msgs[1:]:
                    q.append(msg_to_json(m))
                json_out.append({
                        "is_quote": True,
                        "pinner": None,
                        "pin_timestamp": None,
                        "messages": q})
            else:
                b = msg_to_json(brick)
                b["is_quote"] = False
                json_out.append(b)
        outpath = os.path.join(outdir, serverdir)
        if not os.path.isdir(outpath):
            os.makedirs(outpath)
        with open(os.path.join(outpath, os.path.splitext(fi)[0]) + ".json", "w") as out:
            json.dump(json_out, out)

