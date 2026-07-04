# coding: utf-8
import requests
import json
import sys
import os


# QAX OCR API configuration
API_KEY = '46237bfb0bd554b423fb09114d22e1d0d8677861'
API_URL = 'https://aip.b.qianxin-inc.cn/api/v2.0/cv/ocr_vl'


def ocr_pdf_with_qax_api(pdf_path, output_path=None):
    """
    OCR a PDF file using QAX OCR API

    Arguments:
        pdf_path: Path to the PDF file
        output_path: Output file path (optional, defaults to pdf_path with .md extension)

    Returns:
        dict: Result containing status, pages, characters, and output_path
    """
    if output_path is None:
        # Replace .pdf extension with .md
        base, ext = os.path.splitext(pdf_path)
        if ext.lower() == '.pdf':
            output_path = base + '.md'
        else:
            output_path = pdf_path + '.md'

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'User-Agent': 'QAgent/1.0.0',
    }

    # Check if file exists
    if not os.path.exists(pdf_path):
        return {
            'success': False,
            'error': f'File not found: {pdf_path}'
        }

    try:
        with open(pdf_path, 'rb') as pdf_file:
            resp = requests.post(API_URL, verify=False, headers=headers, files={'image_file': pdf_file})

        print(f'Status code: {resp.status_code}')

        result = resp.json()

        if result.get('status') == 1000:
            print('OCR recognition successful')

            # Extract text content
            text_list = result.get('result', {}).get('text', [])

            # Merge all pages text
            all_text = '\n\n'.join(text_list)

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(all_text)

            print(f'Written to file: {output_path}')
            print(f'Recognized pages: {len(text_list)}')
            print(f'Total characters: {len(all_text)}')

            # Show preview (first 200 characters)
            preview = all_text[:200].replace('\n', ' ')
            print(f'Preview: {preview}...')

            return {
                'success': True,
                'pages': len(text_list),
                'chars': len(all_text),
                'output_path': output_path,
                'preview': preview
            }
        else:
            print(f'OCR recognition failed: {result}')
            return {
                'success': False,
                'error': f'API returned status {result.get("status")}: {result}'
            }

    except requests.exceptions.RequestException as e:
        print(f'API request failed: {e}')
        return {
            'success': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        print(f'Unexpected error: {e}')
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: ocr_with_qax_api.py <input_pdf> [output_md]')
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    result = ocr_pdf_with_qax_api(pdf_file, output_file)

    if result['success']:
        print(f'\nSuccess! Recognized {result["pages"]} pages with {result["chars"]} characters.')
        print(f'Output saved to: {result["output_path"]}')
    else:
        print(f'\nFailed: {result["error"]}')
        sys.exit(1)