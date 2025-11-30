#!/usr/bin/env python3
"""Create YouTube to H5P Moodle Pipeline workflow in n8n"""

import httpx
import json
import os

api_url = os.getenv('N8N_API_URL')
api_key = os.getenv('N8N_API_KEY')

headers = {
    'X-N8N-API-KEY': api_key,
    'Content-Type': 'application/json'
}

workflow_data = {
    'name': 'YouTube to H5P Moodle Pipeline',
    'nodes': [
        {
            'parameters': {
                'httpMethod': 'POST',
                'path': 'youtube-to-h5p',
                'responseMode': 'responseNode',
                'options': {}
            },
            'id': '1',
            'name': 'Webhook - Start',
            'type': 'n8n-nodes-base.webhook',
            'typeVersion': 2,
            'position': [240, 300],
            'webhookId': ''
        },
        {
            'parameters': {
                'resource': 'rows',
                'operation': 'get',
                'tableId': 'youtube_urls',
                'id': '={{ $json.youtube_url_id }}',
                'options': {}
            },
            'id': '2',
            'name': 'Get YouTube URL Row',
            'type': 'n8n-nodes-base.supabase',
            'typeVersion': 1,
            'position': [460, 300]
        },
        {
            'parameters': {
                'rules': {
                    'values': [
                        {
                            'conditions': {
                                'options': {
                                    'leftValue': '',
                                    'caseSensitive': True,
                                    'typeValidation': 'strict'
                                },
                                'conditions': [
                                    {
                                        'leftValue': '={{ $json.subtitles }}',
                                        'rightValue': '',
                                        'operator': {
                                            'type': 'string',
                                            'operation': 'notEmpty'
                                        }
                                    }
                                ],
                                'combinator': 'and'
                            },
                            'renameOutput': True,
                            'outputKey': 'has_subtitles'
                        }
                    ]
                },
                'options': {
                    'fallbackOutput': 'extra'
                }
            },
            'id': '3',
            'name': 'Check Subtitles',
            'type': 'n8n-nodes-base.switch',
            'typeVersion': 3.2,
            'position': [680, 300]
        },
        {
            'parameters': {
                'authentication': 'password',
                'command': 'cd /home/claude/python-modules/src/services/h5p && python3 cli_youtube_to_h5p.py --subtitle-text "={{ $json.subtitles }}" --title "={{ $json.title }}" --createcourse --coursename "={{ $json.title }} - Kurs"'
            },
            'id': '4',
            'name': 'Generate H5P Course',
            'type': 'n8n-nodes-base.ssh',
            'typeVersion': 1,
            'position': [900, 300],
            'credentials': {
                'sshPassword': {
                    'id': '28',
                    'name': 'SSH Password account'
                }
            }
        },
        {
            'parameters': {
                'jsonString': '={{ $json.stdout }}'
            },
            'id': '5',
            'name': 'Parse SSH Output',
            'type': 'n8n-nodes-base.parseJson',
            'typeVersion': 1,
            'position': [1120, 300]
        },
        {
            'parameters': {
                'resource': 'rows',
                'operation': 'update',
                'tableId': 'youtube_urls',
                'id': '={{ $node["Get YouTube URL Row"].json.id }}',
                'updateFields': {
                    'fields': [
                        {
                            'name': 'moodle_course_id',
                            'value': '={{ $json.moodle_course_id }}'
                        }
                    ]
                },
                'options': {}
            },
            'id': '6',
            'name': 'Update YouTube URL',
            'type': 'n8n-nodes-base.supabase',
            'typeVersion': 1,
            'position': [1340, 300]
        },
        {
            'parameters': {
                'respondWith': 'json',
                'responseBody': '={{ { "success": true, "course_id": $json.moodle_course_id, "course_url": "https://moodle.example.com/course/view.php?id=" + $json.moodle_course_id } }}'
            },
            'id': '7',
            'name': 'Respond to Webhook',
            'type': 'n8n-nodes-base.respondToWebhook',
            'typeVersion': 1,
            'position': [1560, 300]
        },
        {
            'parameters': {
                'respondWith': 'json',
                'responseBody': '={{ { "error": "No subtitles available", "youtube_url_id": $json.youtube_url_id } }}'
            },
            'id': '8',
            'name': 'No Subtitles Error',
            'type': 'n8n-nodes-base.respondToWebhook',
            'typeVersion': 1,
            'position': [900, 480]
        }
    ],
    'connections': {
        'Webhook - Start': {
            'main': [
                [
                    {
                        'node': 'Get YouTube URL Row',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        },
        'Get YouTube URL Row': {
            'main': [
                [
                    {
                        'node': 'Check Subtitles',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        },
        'Check Subtitles': {
            'main': [
                [
                    {
                        'node': 'Generate H5P Course',
                        'type': 'main',
                        'index': 0
                    }
                ],
                [],
                [
                    {
                        'node': 'No Subtitles Error',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        },
        'Generate H5P Course': {
            'main': [
                [
                    {
                        'node': 'Parse SSH Output',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        },
        'Parse SSH Output': {
            'main': [
                [
                    {
                        'node': 'Update YouTube URL',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        },
        'Update YouTube URL': {
            'main': [
                [
                    {
                        'node': 'Respond to Webhook',
                        'type': 'main',
                        'index': 0
                    }
                ]
            ]
        }
    },
    'settings': {
        'executionOrder': 'v1'
    }
}

# Create workflow
response = httpx.post(
    f'{api_url}/workflows',
    headers=headers,
    json=workflow_data
)

if response.status_code in [200, 201]:
    workflow = response.json()
    print('[OK] Workflow erfolgreich erstellt!')
    print(f"\nWorkflow ID: {workflow.get('id')}")
    print(f"Name: {workflow.get('name')}")
    print(f"Nodes: {len(workflow.get('nodes', []))}")

    # Activate workflow
    activate_response = httpx.patch(
        f"{api_url}/workflows/{workflow.get('id')}",
        headers=headers,
        json={'active': True}
    )

    if activate_response.status_code == 200:
        print(f"\n[OK] Workflow aktiviert!")

        # Get webhook URL
        for node in workflow.get('nodes', []):
            if node.get('type') == 'n8n-nodes-base.webhook':
                webhook_path = node.get('parameters', {}).get('path', '')
                webhook_url = f"https://srv947487.hstgr.cloud/webhook/{webhook_path}"
                print(f"\nWebhook URL: {webhook_url}")
                break

    print("\n[Nodes] Node Connections:")
    for node in workflow.get('nodes', []):
        print(f"  - {node.get('name')} ({node.get('type')})")
else:
    print(f'[ERROR] HTTP {response.status_code}')
    print(response.text)
