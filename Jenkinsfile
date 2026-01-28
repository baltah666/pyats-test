pipeline {
    agent any

    environment {
        PYTHON_BIN = "/usr/bin/python3.11"
        VENV_DIR   = "pyats-venv"
        REQ_FILE   = "requirements-pyats-24.3-python311.txt"
    }

    stages {

        /* ---------------------------------------------------------
         * Task 1 – Clone repository
         * --------------------------------------------------------- */
        stage('Task 1 - Clone repository') {
            steps {
                echo "Repository cloned by Jenkins automatically (SCM)"
            }
        }

        /* ---------------------------------------------------------
         * Task 2.1 – Verify Python version
         * --------------------------------------------------------- */
        stage('Task 2.1 - Verify Python 3.11') {
            steps {
                sh '''
                set -e
                echo "Using Python:"
                ${PYTHON_BIN} --version
                '''
            }
        }

        /* ---------------------------------------------------------
         * Task 2.2 – Create virtual environment
         * --------------------------------------------------------- */
        stage('Task 2.2 - Create virtualenv') {
            steps {
                sh '''
                set -e
                if [ ! -d "${VENV_DIR}" ]; then
                    echo "Creating virtualenv ${VENV_DIR}"
                    ${PYTHON_BIN} -m venv ${VENV_DIR}
                else
                    echo "Virtualenv already exists, reusing it"
                fi
                '''
            }
        }

        /* ---------------------------------------------------------
         * Task 2.3 – Install Python dependencies
         * --------------------------------------------------------- */
        stage('Task 2.3 - Install Python dependencies') {
            steps {
                sh '''
                set -e
                . ${VENV_DIR}/bin/activate

                pip install --upgrade pip
                pip install -r ${REQ_FILE}
                '''
            }
        }

        /* ---------------------------------------------------------
         * Task 2.4 – Verify pyATS environment (FIXED)
         * --------------------------------------------------------- */
        stage('Task 2.4 - Verify pyATS environment') {
            steps {
                sh '''
                set -e
                . ${VENV_DIR}/bin/activate

                echo "Python version:"
                python --version

                echo "pyATS CLI version:"
                pyats version

                echo "Verifying core imports:"
                python - << 'EOF'
import pyats
import unicon
import genie
print("pyATS / Unicon / Genie imports OK")
EOF
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Task 1 + Task 2 completed successfully"
        }
        failure {
            echo "❌ Pipeline failed — check logs above"
        }
    }
}
