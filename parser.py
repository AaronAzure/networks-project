dictionary={}

def actionset(digit):
    return str('actionset'+str(digit))

def parse(filename):
    lines=[]
    actionsets=[]
    
    with open(filename) as f:
        for line in f:
            if '#' not in line and line[0]!='\n':
                line=line.strip()
                line=line.split(" ")
                if '' in line:
                    line.remove('')
                if 'PORT' in line:
                    dictionary['PORT']=int(line[-1])
                if 'HOSTS' in line:
                    dictionary['HOSTS']=line[2::]
                lines.append(' '.join(line))
    i=1
    count=0
    for line in lines:
        if  actionset(i) in line:
            for line in  lines[(count):]:
                if actionset(i+1) in line:
                    break
                actionsets.append(line)
                
            dictionary[actionset(i)]=actionsets[1::]
            actionsets.clear()
            
            i+=1                
        count+=1    
    print(dictionary)



parse("a.txt")