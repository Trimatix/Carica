import carica
import testModule

# carica.makeDefaultCfg(testModule)
carica.loadCfg(testModule, "testCfg.toml")
print(testModule.validSerializableVar.myField)
