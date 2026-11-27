"""Bounded process-memory cache for opt-in local inference; no disk or secrets."""
import copy, hashlib, json, re, threading, time, uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from .v4_provider import ProviderError, MAX_REQUEST, MAX_RESPONSE, validated_result

PROMPT_VERSION="v4-20261127-3"

class MemoryCache:
    def __init__(self, max_entries=32, max_bytes=4*1024*1024, ttl=300, clock=time.monotonic):
        self.max_entries=max_entries; self.max_bytes=max_bytes; self.ttl=ttl; self.clock=clock
        self.rows=OrderedDict(); self.bytes=0; self.epoch=0; self.lock=threading.Lock()
    def _prune(self):
        now=self.clock()
        for key in list(self.rows):
            if now-self.rows[key][0]>=self.ttl:
                self.bytes-=len(self.rows.pop(key)[1])
    def get(self,key):
        with self.lock:
            self._prune(); row=self.rows.get(key)
            if row is None:return None,self.epoch
            self.rows.move_to_end(key)
            return json.loads(row[1]),self.epoch
    def put(self,key,value,epoch):
        raw=json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode()
        if len(raw)>min(MAX_RESPONSE*2,self.max_bytes):return
        with self.lock:
            if epoch!=self.epoch:return
            self._prune()
            if key in self.rows:self.bytes-=len(self.rows.pop(key)[1])
            self.rows[key]=(self.clock(),raw);self.bytes+=len(raw)
            while len(self.rows)>self.max_entries or self.bytes>self.max_bytes:
                _,old=self.rows.popitem(last=False);self.bytes-=len(old[1])
    def clear(self):
        with self.lock:
            self.rows.clear();self.bytes=0;self.epoch+=1
    def status(self):
        with self.lock:
            self._prune()
            return {"entries":len(self.rows),"bytes":self.bytes,"max_entries":self.max_entries,
                    "max_bytes":self.max_bytes,"ttl_seconds":self.ttl,
                    "scope":"Opt-in local-model responses in process memory only; no persistent cache."}

CACHE=MemoryCache()

def local_revision(model):
    from .v4_provider import model_inventory
    for item in model_inventory():
        if item.get("name")==model and re.fullmatch(r"[0-9a-f]{64}",str(item.get("digest",""))):
            return item["digest"]
    return None

@dataclass
class CachedLocalProvider:
    provider:object
    cache:MemoryCache=field(default_factory=lambda:CACHE)
    revision_lookup:object=local_revision
    usage:dict=field(default_factory=dict,init=False)
    @property
    def model(self):return self.provider.model
    def propose(self,task,data,schema):
        from .v4_provider import TASKS
        self.usage={}
        if task not in TASKS:raise ProviderError("unsupported_task")
        request=json.dumps({"task":task,"data":data,"schema":schema},sort_keys=True,ensure_ascii=True,allow_nan=False).encode()
        if len(request)>MAX_REQUEST:raise ProviderError("request_too_large")
        revision=self.revision_lookup(self.model)
        if not revision:
            result=self.provider.propose(task,data,schema)
            self.usage={**getattr(self.provider,"usage",{}),"cache":"bypassed_missing_model_revision"}
            return result
        identity={"provider":"ollama","model":self.model,"revision":revision,"context":getattr(self.provider,"context",None),
                  "prompt_version":PROMPT_VERSION,"request_sha256":hashlib.sha256(request).hexdigest()}
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        start=time.monotonic();cached,epoch=self.cache.get(key)
        if cached is not None:
            result=validated_result(cached["response"],schema)
            self.usage={"request_id":uuid.uuid4().hex,"cache":"hit","model_revision":revision,
                        "elapsed_ms":round((time.monotonic()-start)*1000,2),"eval_count":0,
                        "source_usage":cached["usage"]}
            return copy.deepcopy(result)
        result=validated_result(self.provider.propose(task,data,schema),schema)
        usage=dict(getattr(self.provider,"usage",{}))
        self.cache.put(key,{"response":result,"usage":usage},epoch)
        self.usage={**usage,"cache":"miss","model_revision":revision}
        return result

def cache_local(provider,enabled):
    if not enabled:return provider
    return CachedLocalProvider(provider)
