pipeline {
    agent any

    parameters {
        text(
            name: 'CONFIG_COMMANDS',
            defaultValue: '',
            description: 'CLI configuration commands to push (multi-line supported)'
        )

        // Requires "Extended Choice Parameter" plugin
        extendedChoice(
            name: 'TESTBEDS',
            type: 'PT_CHECKBOX',
            description: 'Select one or more target testbeds',
            value: '''
testbed_access_9200.yaml,
testbed_access_9300.yaml,
testbed_access_2960.yaml,
testbed_datacenter_n9k.yaml,
testbed_routers.yaml,
testbed_industrial.yaml,
testbed_core_9500.yaml
''',
            multiSelectDelimiter: ','
        )
    }

    environment {
        PYTHON_BIN = "/usr/bin/python3.11"
        VENV_DIR   = "pyats-venv"
    }

    stages {

        stage('Task 1 - Checkout SCM (Clone repo)') {
            steps {
                checkout scm
                sh 'echo "✅ Repo checked out (SCM)"'
            }
        }

        stage('Task 2.1 - Verify Python 3.11') {
            steps {
                sh '''
                set -e
                echo "Using Python:"
                ${PYTHON_BIN} --version
                '''
            }
        }

        stage('Task 2.2 - Create / Reuse Virtualenv') {
            steps {
                sh '''
                set -e
                if [ ! -d "${VENV_DIR}" ]; then
                    ${PYTHON_BIN} -m venv ${VENV_DIR}
                else
                    echo "Virtualenv already exists, reusing it"
                fi
                '''
            }
        }

        stage('Task 2.3 - Install Python dependencies') {
            steps {
                sh '''
                set -e
                . ${VENV_DIR}/bin/activate
                pip install --upgrade pip
                pip install -r requirements-pyats-24.3-python311.txt
                '''
            }
        }

        stage('Task 2.4 - Verify pyATS / Genie / Unicon imports') {
            steps {
                sh '''
                set -e
                . ${VENV_DIR}/bin/activate
                python - << 'PY'
import pyats
import genie
import unicon
print("pyATS import OK")
print("Genie import OK")
print("Unicon import OK")
PY
                '''
            }
        }

        stage('Task 3 - Run pyATS Config Push') {
            steps {
                sh '''
                set -e
                . ${VENV_DIR}/bin/activate
                python config_parallel__access-05.py
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Pipeline completed successfully"
        }
        failure {
            echo "❌ Pipeline failed — check logs above"
        }
    }
}
