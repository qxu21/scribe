import os
import os.path
#[2018-02-23T02:28:23] SpockMan02#4611: Coolio
#0123456789012345678901234567890123456789

def msg_to_json(msg):
    uend = msg.find("#")+5
    b = dict(
            ("id", None),
            ("timestamp", msg[0:21]),
            ("user", msg[22:uend])
            ("content", msg[uend+2:]))

pindir = os.path.join(os.getcwd(),'pins')
for serverdir in os.listdir(pindir):
    for fi in os.listdir(serverdir):
        with open(fi) as f:
            t = f.read()
        # list of blocks that need to be crunched into bricks due to old format suck
        protobricks = re.split(t,r'\n{2,}') 
        bricks_list = [] # list of bricks
        # crunch protobricks into bricks
        for brick in protobricks:
            if (not line.startswith("[")) and len(bricks_list) != 0:
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
                q = []
                msgs = brick.split('\n[')
                # i have regrets
                q.append(msg_to_json(msgs[0]))
                for m in msgs[1:]:
                    q.append('[' + msg_to_json(l))
                json_out.append(q)
            else:
                json_out.append(msg_to_json(brick))
        with open(os.path.join(serverdir, os.path.splitext(fi)[0]) + ".json", "w") as out:
            json.dump(json_out, out)

