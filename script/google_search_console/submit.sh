#!/bin/bash

# Google Search Console URL Submission Wrapper Script
# This script provides convenient shortcuts for common operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/submit_posts.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check dependencies
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi

    # Check if required packages are installed
    python3 -c "import google.auth, googleapiclient.discovery" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_warning "Required Python packages not found. Installing..."
        pip3 install -r "$SCRIPT_DIR/requirements.txt"
        if [ $? -ne 0 ]; then
            print_error "Failed to install dependencies"
            exit 1
        fi
    fi
}

# Function to show usage
show_usage() {
    echo "Google Search Console URL Submission Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  recent [DAYS]     Submit posts modified in the last N days (default: 7)"
    echo "  git [SINCE]       Submit posts changed since git commit (default: HEAD~1)"
    echo "  url URL           Submit a specific URL"
    echo "  setup             Setup credentials and configuration"
    echo "  test              Run in dry-run mode to test configuration"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 recent 3       # Submit posts from last 3 days"
    echo "  $0 git HEAD~5     # Submit posts changed in last 5 commits"
    echo "  $0 url https://thinhdanggroup.github.io/my-post/"
    echo "  $0 test           # Test what would be submitted"
    echo ""
}

# Function to setup credentials
setup_credentials() {
    print_status "Setting up Google Search Console credentials..."

    if [ ! -f "$SCRIPT_DIR/credentials.json" ]; then
        print_warning "credentials.json not found"
        echo ""
        echo "To setup credentials:"
        echo "1. Go to https://console.cloud.google.com/"
        echo "2. Enable Google Search Console API"
        echo "3. Create OAuth2 credentials (Desktop Application)"
        echo "4. Add redirect URI: http://localhost:8080/"
        echo "5. Download and save as: $SCRIPT_DIR/credentials.json"
        echo ""
        read -p "Press Enter when you have placed credentials.json in the script directory..."

        if [ ! -f "$SCRIPT_DIR/credentials.json" ]; then
            print_error "credentials.json still not found. Setup incomplete."
            exit 1
        fi
    fi

    # Create default config if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/config.json" ]; then
        print_status "Creating default configuration..."
        python3 "$PYTHON_SCRIPT" --create-config
    fi

    print_success "Setup complete! You can now run the script."
}

# Function to run the Python script with error handling
run_python_script() {
    python3 "$PYTHON_SCRIPT" "$@"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        print_success "Operation completed successfully"
    else
        print_error "Operation failed with exit code $exit_code"
        exit $exit_code
    fi
}

# Main script logic
main() {
    # Check dependencies first
    check_dependencies

    # Parse command
    case "${1:-recent}" in
        recent)
            days="${2:-7}"
            print_status "Submitting posts from last $days days..."
            run_python_script --mode recent --days "$days"
            ;;
        git)
            since="${2:-HEAD~1}"
            print_status "Submitting posts changed since $since..."
            run_python_script --mode git --since "$since"
            ;;
        url)
            if [ -z "$2" ]; then
                print_error "URL is required for 'url' command"
                show_usage
                exit 1
            fi
            print_status "Submitting URL: $2"
            run_python_script --mode url --url "$2"
            ;;
        setup)
            setup_credentials
            ;;
        test)
            print_status "Running in test mode (dry-run)..."
            run_python_script --dry-run --verbose
            ;;
        help|-h|--help)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"