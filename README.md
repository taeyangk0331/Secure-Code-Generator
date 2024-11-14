# Secure-Code-Generator

이 프로그램은 ChatGPT가 생성하는 코드의 취약점을 보완하기 위한 파인튜닝된 모델입니다.

# Install

아래에 있는 링크를 클릭하시고 Source code와 model.safetensors를 다운 받습니다. model.safetensors 경우 model 폴더에 저장합니다.

https://github.com/taeyangk0331/Secure-Code-Generator/releases/tag/main

필요한 라이브러리는 ```make```를 입력하시면 설치가 완료되며 실행을 위해서 ```make run```을 입력하시면 실행이 됩니다.

실행이 완료되면 아래의 이미지처럼 링크를 ctrl + 클릭을 하시면 브라우져가 뜹니다.

![image](https://github.com/user-attachments/assets/438cf116-9a26-42f9-8c68-e74b9841884f)

## 커멘드 라인 환경에서 HTTP 요청 보내는 방법

```
curl -X POST "http://0.0.0.0:5059/api/generate/" -H "Content-Type: application/json" -d '{"prompt": "Generate python code for the following: \nA decorator tells the web application what URL should trigger our function.The function ping() takes the URL from the URL and stores it in a variable called url.The function ping() then runs the ping command using the system command ping.The output of the ping command is stored in a variable called output.The function ping() returns the output of the ping command."}'
```
# Codeql 설치 및 세팅

## Codeql 설치

```
wget https://github.com/github/codeql-cli-binaries/releases/download/v2.19.3/codeql-linux64.zip
```

설치가 완료 되었으면 압축 해제합니다.

```
unzip codeql-linux64.zip -d ~/codeql
```

압축 해제가 완료가 되었으면 Codeql 실행 파일이 포함된 디렉터리로 환경 변수 PATH을 추가합니다
```
echo 'export PATH="$PATH:$HOME/codeql/codeql"' >> ~/.bashrc
source ~/.bashrc
```

PATH 추가를 원하시지 않으면 ```cd ~/codeql/codeql``` 로 들어가셔서 ```./codeql```을 사용하셔도 됩니다.

## Codeql 데이터베이스 생성

```
codeql database create <데이터베이스 이름> --language=<언어> --source-root=<소스 코드 디렉토리>
```

예를 들어, data 폴더에 있는 python 언어의 데이터베이스를 생성할려면 아래와 같이 입력하시면 됩니다.

```
codeql database create database --language=python --source-root=./data
```

## llmseceval queries 설치 및 세팅

저희가 사용한 queries 경우 codeql에 저장되어 있는 queries가 아닌 llmseceval queries를 따로 사용하였기에 llmseceval도 설치해야합니다.

# llmseceval 설치

```
git clone https://github.com/tuhh-softsec/LLMSecEval.git
```

# llmseceval Queries 실행

```
codeql database analyze <데이터베이스 폴더 위치> ./LLMSecEval/Security\ Analysis\ -\ CodeQL/Queries/py/top25/python-top25.qls --format=csv --output=results.csv
```

이 커멘드를 입력을 하면 이 에러가 뜰 수 있습니다

```
ERROR: Pack 'codeql/python-all@0.6.2' was not found in the pack download cache. Run 'codeql pack install' to download the dependencies. (/LLMSecEval/Security Analysis - CodeQL/Queries/py/top25/qlpack.yml:1,1-1)
ERROR: No valid pack solution found:
Because 'mutasdev/python-top25-queries' depends on 'codeql/python-all@*', but pack 'codeql/python-all' was not found, version solving failed.
 (/home/becreative/team_project/LLMSecEval/Security Analysis - CodeQL/Queries/py/top25/qlpack.yml:1,1-1)
A fatal error occurred: A 'codeql resolve extensions-by-pack' operation failed with error code 2
```

queries 폴더로 이동
```
cd /LLMSecEval/Security\ Analysis\ -\ CodeQL/Queries/py/top25
```

codeql pack 설치

```
codeql pack install
```

다시 queries 실행

```
codeql database analyze ./new_data/new_data ./LLMSecEval/Security\ Analysis\ -\ CodeQL/Queries/py/top25/python-top25.qls --format=csv --output=results.csv
```

폴더에 results.csv가 저장되어 있는걸 확인 할 수 있습니다.

![image](https://github.com/user-attachments/assets/9adb6f5b-d89d-4383-8647-8be3d2256e0a)
