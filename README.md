<p align="center">
  <img
    width="256"
    src="https://i.imgur.com/X4sdZt7.png"
    alt="Carica Logo"
  />
</p>
<h1 align="center">Carica - A Python Configurator</h1>
<p align="center">
  <a href="https://github.com/Trimatix/Carica/actions"
    ><img
      src="https://img.shields.io/github/workflow/status/GOF2BountyBot/GOF2BountyBot/BASED"
      alt="GitHub Actions workflow status"
  /></a>
  <a href="https://github.com/Trimatix/Carica/projects/1?card_filter_query=label%3Abug"
    ><img
      src="https://img.shields.io/github/issues-search?color=eb4034&label=bug%20reports&query=repo%3ATrimatix%2FCarica%20is%3Aopen%20label%3Abug"
      alt="GitHub open bug reports"
  /></a>
  <a href="https://github.com/Trimatix/Carica/actions"
    ><img
      src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Trimatix/2551cac90336c1d1073d8615407cc72d/raw/Carica__heads_main.json"
      alt="Test coverage"
  /></a>
</p>
<p align="center">
  <a href="https://pypi.org/project/Carica"
    ><img
      src='https://badgen.net/pypi/v/Carica/'
      alt="Pypi package version"
  /></a>
  <a href="https://pypi.org/project/Carica"
    ><img
      src="https://img.shields.io/pypi/pyversions/Carica.svg"
      alt="Minimum supported Python version"
  /></a>
  <a href="https://github.com/Trimatix/Carica/blob/master/LICENSE"
    ><img
      src="https://img.shields.io/github/license/Trimatix/Carica.svg"
      alt="License"
</p>
<p align="center">
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_Carica"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_Carica&metric=bugs"
      alt="SonarCloud bugs analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_Carica"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_Carica&metric=code_smells"
      alt="SonarCloud code smells analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=Trimatix_Carica"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=Trimatix_Carica&metric=alert_status"
      alt="SonarCloud quality gate status"
  /></a>
</p>


Carica is a python application configurator, interfacing between a pure python config module, and TOML representation of that module.

<hr>

### Credits
A huge thank you goes to [@sdispater](https://github.com/sdispater), author of the fantastic [tomlkit library](https://github.com/sdispater/tomlkit), which makes this project's variable docstrings retaining features possible.

## Project Goals
Python applications can be configured in a number of ways, each with its own advantages and limitations.
<details>
<summary>Common Configuration Methods</summary>
<table>
	<tbody>
	<tr>
		<th align="center">Method</th>
		<th align="center">Advantages</th>
		<th align="center">Problems</th>
	</tr>
	<tr>
		<td>Environment variables/Command line arguments</td>
		<td>
			<ul>
				<li>Easy to handle in code</li>
				<li>Container/venv safe</li>
			</ul>
		</td>
		<td>
			<ul>
				<li>Not scalable to large numbers of variables</li>
				<li>Primative data types only</li>
				<li>Not human-friendly</li>
				<li>No typing in code</li>
				<li>No code autocompletion or other editor features</li>
				<li>Difficult to version control</li>
			</ul>
		</td>
	</tr>
	<tr>
		<td>TOML config file</td>
		<td>
			<ul>
				<li>Container/venv safe</li>
				<li>More scalable</li>
				<li>More expressive, with tables</li>
				<li>Easy to version control</li>
				<li>Human friendly</li>
			</ul>
		</td>
		<td>
			<ul>
				<li>Not easy to manage in code</li>
				<li>No code autocompletion or other editor features</li>
				<li>No dot syntax for objects</li>
				<li>No typing in code</li>
			</ul>
		</td>
	</tr>
	<tr>
		<td>Python module with variables</td>
		<td>
			<ul>
				<li>Easy to handle in code</li>
				<li>Easy to version control, with rich, human-readable diffs</li>
				<li>Highly scalable</li>
				<li>Completely expressive</li>
				<li>Dot syntax for objects</li>
				<li>Variable typing in code</li>
				<li>Complete language and editor features</li>
			</ul>
		</td>
		<td>
			<ul>
				<li>Not container/venv safe</li>
				<li>Not human-friendly</li>
				<li>Module must be accessible to the application namespace - difficult for packages</li>
			</ul>
		</td>
	</tr>
	</tbody>
</table>
</details>

Carica aims to mix the best bits from two of the most convenient configuration methods, acting as an interface between pure python modules and TOML config files.

## Basic Usage
To use Carica, your application configuration should be defined as a python module.

<details>
<summary>Example Application</summary>

*loginApp.py*
```py
import cfg
import some_credentials_manager
import re

print(cfg.welcome_message)
new_user_data = {}

for field_name, field_config in cfg.new_user_required_fields.items():
    print(field_config['display'] + ":")
    new_value = input()
    if re.match(new_value, field_config['validation_regex']):
        new_user_data[field_name] = new_value
    else:
        raise ValueError(f"The value for {field_name} did not pass validation")

some_credentials_manager.create_user(new_user_data)
```

*cfg.py*
```py
welcome_message = "Welcome to the application. Please create an account:"

new_user_required_fields = {
    "username": {
        "display": "user-name",
        "validation_regex": "[a-z]+"
    },
    "password": {
        "display": "pw",
        "validation_regex": "\\b(?!password\\b)\\w+"
    },
}
```
</details>

#### Default config generation
Carica is able to auto-generate a default TOML config file for your application, with the values specified in your python module as defaults:

```py
>>> import cfg
>>> import carica
>>> carica.makeDefaultCfg(cfg)
Created defaultCfg.toml
```

The above code will produce the following file:

*defaultCfg.toml*
```toml
welcome_message = "Welcome to the application. Please create an account:"

[new_user_required_fields]
[new_user_required_fields.username]
display = "user-name"
validation_regex = "[a-z]+"
    
[new_user_required_fields.password]
display = "pw"
validation_regex = "\\b(?!password\\b)\\w+"
```

### Loading a configuration file
Carica will map the variables given in your config file to those present in your python module.
Since the config python module contains default values, Carica does not require every variable to be specified:

*myConfig.toml*
```toml
[new_user_required_fields]
[new_user_required_fields.avatar]
display = "profile picture"
validation_regex = "[a-z]+"
```


```py
>>> import cfg
>>> import carica
>>> carica.loadCfg(cfg, "myConfig.toml")
Config successfully loaded: myConfig.toml
>>> import loginApp
Welcome to the application. Please create an account:
profile picture:
123
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "loginApp.py", line 14, in <module>
    raise ValueError(f"The value for {field_name} did not pass validation")
ValueError: The value for avatar did not pass validation
```

### Variable Pseudo-Docstrings
When encountering a comment in your python config module, Carica will treat it as a variable 'docstring' in the following cases:

1. Inline comments on the same line as a variable declaration
2. Line comments immediately preceeding a variable declaration ('preceeding comments') *\*Beta feature: still in testing\**
3. Line comments immediately preceeding an existing preceeding comment *\*Beta feature: still in testing\**

Carica will consider your variable docstrings when building TOML config files:

*cfg.py*
```py
# This is shown to the user when the application is first launched
# No validation is performed on this string
welcome_message = "Welcome to the application. Please create an account:"

new_user_required_fields = { # Each field should specify a 'display' (formatted field name shown to users) and a 'validation_regex', which inputted values will be checked against
    "username": {
        "display": "user-name",
        "validation_regex": "[a-z]+"
    },
    "password": {
        "display": "pw",
        "validation_regex": "\\b(?!password\\b)\\w+"
    },
}
```

```py
>>> import cfg
>>> import carica
>>> carica.makeDefaultCfg(cfg)
Created defaultCfg.toml
```

The above code will produce the following file:

*defaultCfg.toml*
```toml
# This is shown to the user when the application is first launched
# No validation is performed on this string
welcome_message = "Welcome to the application. Please create an account:"

[new_user_required_fields] # Each field should specify a 'display' (formatted field name shown to users) and a 'validation_regex', which inputted values will be checked against
[new_user_required_fields.username]
display = "user-name"
validation_regex = "[a-z]+"
    
[new_user_required_fields.password]
display = "pw"
validation_regex = "\\b(?!password\\b)\\w+"
```

## Advanced Usage
Carica will handle non-primative variable types according to a very simple design pattern:

### The `SerializableType` type protocol
```py
class SerializableType:
    def serialize(self, **kwargs): ...

    @classmethod
    def deserialize(cls, data, **kwargs): ...
```

Any type which defines `serialize` and `deserialize` member methods will be automatically serialized during config generation, and deserialized on config loading.

- `serialize` must return a representation of your object with primative types - types which can be written to toml.
- `deserialize` must be a class method, and should transform a serialized object representation into a new object.

Carica enforces this pattern on non-primative types using the `SerializableType` type protocol, which allows for duck-typed serializable types. This protocol is exposed for use with `isinstance`.

Projects which prefer strong typing may implement the `carica.ISerializable` interface to enforce this pattern with inheritence. Carica will validate serialized objects against the `carica.PrimativeType` type alias, which is also exposed for use.

### Example

*cfg.py*
```py
from carica import ISerializable

class MySerializableType(ISerializable):
    def __init__(self, myField):
        self.myField = myField

    def serialize(self, **kwargs):
        return {"myField": self.myField}

    @classmethod
    def deserialize(self, data, **kwargs):
        return MySerializableClass(data["myField"])

mySerializableVar = MySerializableClass("hello")
```

#### Default config generation
```py
>>> import cfg
>>> import carica
>>> carica.makeDefaultCfg(cfg)
Created defaultCfg.toml
```

The above code will produce the following file:

*defaultCfg.toml*
```toml
[mySerializableVar]
myField = "hello"
```

#### Config file loading
*myConfig.toml*
```toml
[mySerializableVar]
myField = "some changed value"
```

```py
>>> import cfg
>>> import carica
>>> carica.loadCfg(cfg, "myConfig.toml")
Config successfully loaded: myConfig.toml
>>> cfg.mySerializableVar.myField
some changed value
```

### Premade models
Carica provides serializable models that are ready to use (or extend) in your code. These models can be found in the `carica.models` package, which is imported by default.

#### SerializableDataClass
Removes the need to write boilerplate serializing functionality for dataclasses. This class is intended to be extended, adding definitions for your dataclass's fields. Extensions of `SerializableDataClass` **must** themselves be decorated with `@dataclasses.dataclass` in order to function correctly.

#### SerializablePath
An OS-agnostic filesystem path, extending `pathlib.Path`. The serializing/deserializing behaviour added by this class is minimal, a serialized `SerializablePath` is simply the string representation of the path, for readability. All other behaviour of `pathlib.Path` applies, for example. `SerializablePath` can be instantiated from a single path: `SerializablePath("my/directory/path")`, or from path segments: `SerializablePath("my", "file", "path.toml")`.

#### SerializableTimedelta
`datetime.datetime` is already considered a primitive type by TomlKit, and so no serializability needs to be added for you to use this class in your configs. However, `datetime.timedelta` is not serializable by default. `SerializableTimedelta` solves this issue as a serializable subclass. As a subclass, all `timedelta` behaiour applies, including the usual constructor. In addition, `SerializableTimedelta.fromTimedelta` is a convenience class method that accepts a `datetime.timedelta` and constructs a new `SerializableTimedelta` from it.

#### Premade models example
The recommended usage pattern for `SerializableDataClass` is to separate your models into a separate module/package, allowing for 'schema' definition as python code. This pattern is not necessary, model definition *can* be done in your config file.

*configSchema.py*
```py
from carica.models import SerializableDataClass
from dataclasses import dataclass

@dataclass
class UserDataField(SerializableDataClass):
    name: str
    validation_regex: str
```
*config.py*
```py
from carica.models import SerializablePath, SerializableTimedelta
from configSchema import UserDataField
from datetime import datetime

new_user_required_fields = [
    UserDataField(
        name = "user-name"
        validation_regex = "[a-z]+"
    ),

    UserDataField(
        name = "password"
        validation_regex = "\\b(?!password\\b)\\w+"
    )
]

database_path = SerializablePath("default/path.csv")
birthday = datetime(day=1, month=1, year=1500)
connection_timeout = SerializableTimedelta(minutes=5)
```


## Planned features
- Preceeding comments: This functionality is 'complete' in that it functions as intended and passes all unit tests, however an issue needs to be worked aruond before the feature can be enabled: In order to disambiguate between variables and table fields, the TOML spec requires that arrays and tables be placed at the end of a document. Carica currently depends upon documents being rendered with variables appearing in the same order as they appear in the python config module, which is not guaranteed. This leads to trailing and otherwise misplaced preceeding comments.
- Config mutation: Carica should allow for loading an existing config, changing some values, and then updating the TOML document with new values. This should retain all formatting from the original document, including variable ordering and any comments that are not present in the python module.
## Limitations
- No support for schema migration
- No support for asynchronous object serializing/deserializing
- Imperfect estimation of variables defined in python modules: Listing the variables defined within a scope is not a known feature of python, and so Carica estimates this information by iterating over the tokens in your module. Carica does not build an AST of your python module.

    This means that certain name definition structures will result in false positives/negatives. This behaviour has not been extensively tested, but once such false positive has been identified:
    
    When invoking a callable (such as a class or function) with a keyword argument on a new, unindented line, the argument
    name will be falsely identified as a variable name. E.g:
    ```py
    my_variable = dict(key1=value1,
    key2=value2)
    ```
    produces `my_variable` and `key2` as variable names.

